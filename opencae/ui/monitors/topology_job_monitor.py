"""Live density and convergence window for a topology Study job."""

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout

from opencae.ui.viewport.topology_overlay import TopologyDensityOverlay
from opencae.ui.viewport.viewport_factory import create_viewport


class TopologyJobMonitor(QDialog):
    """Show only the latest topology state while the job is running."""

    def __init__(self, store, job_id, parent=None):
        super().__init__(parent)
        self.store = store
        self.job_id = str(job_id)
        self._pending = None
        self.overlay = TopologyDensityOverlay()
        job = store.project.try_resolve(self.job_id)
        self.setWindowTitle(f"Topology Monitor - {getattr(job, 'name', 'Job')}")
        self.resize(980, 720)
        layout = QVBoxLayout(self)
        self.phase = QLabel(getattr(job, "progress_label", "Prepared"))
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.viewport = create_viewport(store)
        self.viewport.set_stage("STUDIES")
        self.viewport.set_display_mode("mesh")
        layout.addWidget(self.phase)
        layout.addWidget(self.progress)
        layout.addWidget(self.viewport, 1)
        self.viewport.request_refresh(fit=True)
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

    def show_frame(self, job_id, run, iteration, mesh_index, density):
        if str(job_id) != self.job_id:
            return
        self._pending = (run, iteration, mesh_index, density)
        QTimer.singleShot(0, self._present_pending)

    def _present_pending(self):
        if self._pending is None:
            return
        run, iteration, mesh_index, density = self._pending
        try:
            self.overlay.show(
                self.viewport,
                run,
                iteration,
                mesh_index,
                density,
                threshold=0.0,
            )
        except Exception as exc:
            self.phase.setText(f"Live visualization failed: {exc}")

    def closeEvent(self, event):
        self.overlay.clear(self.viewport)
        super().closeEvent(event)
