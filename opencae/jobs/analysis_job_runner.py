"""Runs one solver process for a generic Analysis job."""

from copy import deepcopy
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, QTimer, pyqtSignal

from opencae.controllers.background_task import BackgroundTask


_PHASES = (
    ("reading and processing input", 0.08, "Reading input"),
    ("assigning sections", 0.16, "Assigning sections"),
    ("constructing load matrix", 0.28, "Building loads"),
    ("building constraints", 0.38, "Building constraints"),
    ("constructing stiffness", 0.52, "Building stiffness matrix"),
    ("solving", 0.72, "Solving"),
    ("interpolating stress", 0.86, "Post-processing"),
    ("writing", 0.95, "Writing results"),
)


class AnalysisJobRunner(QObject):
    """Prepare and execute one immutable Analysis snapshot without blocking Qt."""

    output = pyqtSignal(str)
    progress = pyqtSignal(float, str)
    finished = pyqtSignal(str, int)

    def __init__(
        self,
        project_snapshot,
        analysis_id,
        adapter,
        executable,
        extra_arguments,
        directory,
        parent=None,
        *,
        deck_profile=None,
    ):
        super().__init__(parent)
        # The caller already supplies the immutable job snapshot.  Do not make a
        # second potentially expensive graph copy on the GUI thread here.
        self.project = project_snapshot
        self.analysis_id = str(analysis_id)
        self.adapter = adapter
        self.executable = str(executable)
        self.extra_arguments = str(extra_arguments or "")
        self.directory = Path(directory)
        self.deck_profile = deepcopy(deck_profile)
        self.output_base = self.directory / "results"
        self.process: QProcess | None = None
        self._prepare_task: BackgroundTask | None = None
        self._stopping = False
        self._completed = False

    def start(self):
        """Render/write the deck on a worker thread, then launch QProcess in Qt."""
        if self._completed or self.process is not None or self._prepare_task is not None:
            return
        self.progress.emit(0.01, "Preparing analysis")
        task = BackgroundTask(
            self._prepare,
            on_result=self._prepared,
            on_error=self._preparation_failed,
            parent=self,
        )
        self._prepare_task = task
        task.start()

    def _prepare(self):
        """Perform deck generation and file I/O outside the GUI thread."""
        analysis = self.project.resolve(self.analysis_id)
        self.directory.mkdir(parents=True, exist_ok=True)
        extension = str(getattr(self.adapter, "deck_extension", ".inp"))
        deck_path = self.directory / f"analysis{extension}"
        text = self.adapter.write_deck_text(
            self.project,
            analysis,
            profile=self.deck_profile,
        )
        deck_path.write_text(text, encoding=_profile_encoding(self.deck_profile))
        command = self.adapter.build_command(
            self.executable,
            deck_path,
            self.output_base,
            self.extra_arguments,
        )
        if not command:
            raise ValueError("The solver adapter produced an empty command")
        return tuple(str(value) for value in command)

    def _prepared(self, command) -> None:
        """Launch the already-prepared command back on the GUI thread."""
        self._prepare_task = None
        if self._completed:
            return
        if self._stopping:
            self._finish(130)
            return

        process = QProcess(self)
        self.process = process
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.setWorkingDirectory(str(self.directory))
        process.readyReadStandardOutput.connect(self._read_output)
        process.finished.connect(self._process_finished)
        process.errorOccurred.connect(self._process_error)
        process.setProgram(str(command[0]))
        process.setArguments([str(value) for value in command[1:]])
        self.progress.emit(0.02, "Starting solver")
        process.start()

    def _preparation_failed(self, error: Exception) -> None:
        self._prepare_task = None
        if self._completed:
            return
        if self._stopping:
            self._finish(130)
            return
        self.output.emit(f"Analysis preparation failed: {error}\n")
        self._finish(1)

    def stop(self):
        """Request cancellation without synchronously waiting on the child process."""
        if self._completed:
            return
        self._stopping = True
        self.progress.emit(0.0, "Stopping")
        process = self.process
        if process is None:
            # Preparation itself cannot safely be force-terminated.  Its result
            # callback observes _stopping and completes the Job as cancelled.
            if self._prepare_task is None:
                self._finish(130)
            return
        if process.state() == QProcess.ProcessState.NotRunning:
            self._finish(130)
            return
        process.terminate()
        QTimer.singleShot(1500, self._kill_if_running)

    def _kill_if_running(self) -> None:
        """Escalate a terminate request asynchronously after the grace period."""
        process = self.process
        if (
            self._stopping
            and process is not None
            and process.state() != QProcess.ProcessState.NotRunning
        ):
            process.kill()

    def _read_output(self):
        if self.process is None:
            return
        text = bytes(self.process.readAllStandardOutput()).decode(errors="replace")
        if not text:
            return
        self.output.emit(text)
        lowered = text.casefold()
        for token, value, label in _PHASES:
            if token in lowered:
                self.progress.emit(value, label)

    def _process_finished(self, code, _status):
        self._read_output()
        process = self.process
        self.process = None
        if process is not None:
            process.deleteLater()
        self._finish(130 if self._stopping else int(code))

    def _process_error(self, error):
        process = self.process
        if process is None or self._completed:
            return
        self.output.emit(f"\nSolver process error: {error.name}\n")
        if process.state() == QProcess.ProcessState.NotRunning:
            self.process = None
            process.deleteLater()
            self._finish(130 if self._stopping else 1)

    def _finish(self, code: int) -> None:
        """Emit the terminal state exactly once."""
        if self._completed:
            return
        self._completed = True
        self.finished.emit(str(self.output_base), int(code))


def _profile_encoding(profile) -> str:
    if profile is not None and str(profile.settings.get("encoding", "")).upper() == "ASCII":
        return "ascii"
    return "utf-8"
