"""Runs one solver process for a generic Analysis job."""

from copy import deepcopy
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, pyqtSignal


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
    """QProcess runner that prepares and executes one immutable Analysis snapshot."""

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
        self.project = deepcopy(project_snapshot)
        self.analysis_id = str(analysis_id)
        self.adapter = adapter
        self.executable = str(executable)
        self.extra_arguments = str(extra_arguments or "")
        self.directory = Path(directory)
        self.deck_profile = deepcopy(deck_profile)
        self.output_base = self.directory / "results"
        self.process = None
        self._stopping = False

    def start(self):
        try:
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
        except Exception as exc:
            self.output.emit(f"Analysis preparation failed: {exc}\n")
            self.finished.emit(str(self.output_base), 1)
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

    def stop(self):
        process = self.process
        if process is None or process.state() == QProcess.ProcessState.NotRunning:
            return
        self._stopping = True
        self.progress.emit(0.0, "Stopping")
        process.terminate()
        if not process.waitForFinished(1500):
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
        final_code = 130 if self._stopping and int(code) == 0 else int(code)
        self.finished.emit(str(self.output_base), final_code)

    def _process_error(self, error):
        process = self.process
        if process is None:
            return
        self.output.emit(f"\nSolver process error: {error.name}\n")
        if process.state() == QProcess.ProcessState.NotRunning:
            self.process = None
            process.deleteLater()
            self.finished.emit(str(self.output_base), 1)


def _profile_encoding(profile) -> str:
    if profile is not None and str(profile.settings.get("encoding", "")).upper() == "ASCII":
        return "ascii"
    return "utf-8"
