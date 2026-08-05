"""Runs one solver process for a generic Analysis job."""

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
    """QProcess-backed runner that streams output into the central job system."""

    output = pyqtSignal(str, str)
    progress = pyqtSignal(str, float, str)
    finished = pyqtSignal(str, int, object)

    def __init__(self, job_id, command, directory, output_base, output_file, parent=None):
        super().__init__(parent)
        self.job_id = str(job_id)
        self.command = tuple(str(value) for value in command)
        self.directory = Path(directory)
        self.output_base = Path(output_base)
        self.output_file = Path(output_file)
        self.process = None
        self._stream = None
        self._stopping = False

    def start(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        self._stream = self.output_file.open("a", encoding="utf-8")
        process = QProcess(self)
        self.process = process
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.setWorkingDirectory(str(self.directory))
        process.readyReadStandardOutput.connect(self._read_output)
        process.finished.connect(self._process_finished)
        process.errorOccurred.connect(self._process_error)
        process.setProgram(self.command[0])
        process.setArguments(list(self.command[1:]))
        self.progress.emit(self.job_id, 0.02, "Starting solver")
        process.start()

    def stop(self):
        process = self.process
        if process is None or process.state() == QProcess.ProcessState.NotRunning:
            return
        self._stopping = True
        self.progress.emit(self.job_id, 0.0, "Stopping")
        process.terminate()
        if not process.waitForFinished(1500):
            process.kill()

    def _read_output(self):
        if self.process is None:
            return
        text = bytes(self.process.readAllStandardOutput()).decode(errors="replace")
        if not text:
            return
        if self._stream is not None:
            self._stream.write(text)
            self._stream.flush()
        self.output.emit(self.job_id, text)
        lowered = text.casefold()
        for token, value, label in _PHASES:
            if token in lowered:
                self.progress.emit(self.job_id, value, label)

    def _process_finished(self, code, _status):
        self._read_output()
        if self._stream is not None:
            self._stream.close()
            self._stream = None
        process = self.process
        self.process = None
        if process is not None:
            process.deleteLater()
        final_code = 130 if self._stopping and int(code) == 0 else int(code)
        self.finished.emit(self.job_id, final_code, self.output_base)

    def _process_error(self, error):
        if self.process is None:
            return
        if self.process.state() == QProcess.ProcessState.NotRunning:
            self.output.emit(
                self.job_id,
                f"\nSolver process error: {error.name}\n",
            )
