"""Progress and solver-output window for a running Analysis Job."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout

from opencae.ui.core.widgets import MonospaceOutputView
from opencae.ui.templates import SectionHeading


class AnalysisJobMonitor(QDialog):
    """Show one Analysis Job's structured progress and its solver output."""

    def __init__(self, store, job_id, parent=None):
        """Build a persistent monitor for one Job id."""
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.job_id = str(job_id)
        job = store.project.try_resolve(self.job_id)
        self.setWindowTitle(
            f"Analysis Monitor - {getattr(job, 'name', 'Job')}"
        )
        self.resize(760, 520)
        self.setMinimumSize(520, 340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        self.phase = QLabel(getattr(job, "progress_label", "Prepared"))
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.output = MonospaceOutputView()

        layout.addWidget(self.phase)
        layout.addWidget(self.progress)
        layout.addWidget(SectionHeading("Solver Output"))
        layout.addWidget(self.output, 1)
        self.set_progress(
            self.job_id,
            getattr(job, "progress", 0.0),
            getattr(job, "progress_label", "Prepared"),
        )

    def set_progress(self, job_id, value, label):
        """Apply a progress event only when it belongs to this monitor's Job."""
        if str(job_id) != self.job_id:
            return
        self.phase.setText(str(label))
        self.progress.setValue(
            round(min(max(float(value), 0.0), 1.0) * 1000)
        )

    def set_output(self, job_id, text):
        """Load the persisted solver transcript when this monitor is opened."""
        if str(job_id) != self.job_id:
            return
        self.output.set_output(text)

    def append_output(self, job_id, text):
        """Append a live solver-output chunk for this monitor's Job."""
        if str(job_id) != self.job_id:
            return
        self.output.append_output(text)
