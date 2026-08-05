"""Progress window for a running Analysis job."""

from PyQt6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout


class AnalysisJobMonitor(QDialog):
    def __init__(self, store, job_id, parent=None):
        super().__init__(parent)
        self.job_id = str(job_id)
        job = store.project.try_resolve(self.job_id)
        self.setWindowTitle(f"Analysis Monitor - {getattr(job, 'name', 'Job')}")
        layout = QVBoxLayout(self)
        self.phase = QLabel(getattr(job, "progress_label", "Prepared"))
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        layout.addWidget(self.phase)
        layout.addWidget(self.progress)
        self.set_progress(
            self.job_id,
            getattr(job, "progress", 0.0),
            getattr(job, "progress_label", "Prepared"),
        )

    def set_progress(self, job_id, value, label):
        if str(job_id) != self.job_id:
            return
        self.phase.setText(str(label))
        self.progress.setValue(round(min(max(float(value), 0.0), 1.0) * 1000))
