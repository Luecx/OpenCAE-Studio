"""Live density and convergence window for a topology Study job."""

from pathlib import Path

import numpy as np
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout

from opencae.model.entities.optimization import OptimizationRun
from opencae.optimization import build_mesh_index
from opencae.ui.viewport.topology_overlay import TopologyDensityOverlay
from opencae.ui.viewport.viewport_factory import create_viewport


class TopologyJobMonitor(QDialog):
    """Show only the latest topology state while preserving all frames on disk."""

    def __init__(self, store, job_id, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.store = store
        self.job_id = str(job_id)
        self._pending = None
        self.overlay = TopologyDensityOverlay()
        job = store.project.try_resolve(self.job_id)
        self.setWindowTitle(
            f"Topology Monitor - {getattr(job, 'name', 'Job')}"
        )
        self.resize(980, 720)
        layout = QVBoxLayout(self)
        self.phase = QLabel(getattr(job, "progress_label", "Prepared"))
        self.metrics = QLabel("Waiting for the first optimization iteration")
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.viewport = create_viewport(store, self)
        self.viewport.set_stage("STUDIES")
        self.viewport.set_display_mode("mesh")
        layout.addWidget(self.phase)
        layout.addWidget(self.metrics)
        layout.addWidget(self.progress)
        layout.addWidget(self.viewport, 1)
        self.viewport.request_refresh(fit=True)
        self.set_progress(
            self.job_id,
            getattr(job, "progress", 0.0),
            getattr(job, "progress_label", "Prepared"),
        )
        QTimer.singleShot(0, self._restore_latest_frame)

    def set_progress(self, job_id, value, label):
        if str(job_id) != self.job_id:
            return
        self.phase.setText(str(label))
        self.progress.setValue(
            round(min(max(float(value), 0.0), 1.0) * 1000)
        )

    def show_frame(self, job_id, run, iteration, mesh_index, density):
        if str(job_id) != self.job_id:
            return
        constraints = ", ".join(
            f"{value:.6g}"
            for value in dict(iteration.constraint_values).values()
        ) or "n/a"
        self.metrics.setText(
            f"Objective {iteration.objective_value:.6g}   "
            f"Constraint {constraints}   "
            f"max Δρ {iteration.maximum_density_change:.3g}"
        )
        self._pending = (run, iteration, mesh_index, density)
        QTimer.singleShot(0, self._present_pending)

    def _restore_latest_frame(self):
        run = next(
            (
                value
                for study in self.store.project.studies
                for value in getattr(study, "runs", ())
                if isinstance(value, OptimizationRun)
                and value.job_ref
                and value.job_ref.entity_id == self.job_id
            ),
            None,
        )
        if run is None or not run.iterations:
            return
        iteration = run.iterations[-1]
        path = Path(iteration.density_file)
        if not path.exists():
            return
        try:
            with np.load(path, allow_pickle=False) as values:
                density = np.asarray(values["physical"], dtype=float).copy()
            mesh_index = build_mesh_index(self.store.project)
        except Exception as exc:
            self.phase.setText(f"Stored visualization failed: {exc}")
            return
        if run.mesh_fingerprint and run.mesh_fingerprint != mesh_index.fingerprint:
            self.phase.setText("The mesh changed since this Study job")
            return
        self.show_frame(
            self.job_id,
            run,
            iteration,
            mesh_index,
            density,
        )

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
