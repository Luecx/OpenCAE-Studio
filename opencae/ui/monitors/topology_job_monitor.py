"""Live density, convergence and solver-output window for a topology Study Job."""

from pathlib import Path

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from opencae.model.entities.optimization import OptimizationRun
from opencae.optimization import (
    active_constraint_limit,
    automatic_density_threshold,
    build_mesh_index,
    load_density_state,
)
from opencae.ui.core.widgets import MonospaceOutputView
from opencae.ui.templates import SectionHeading
from opencae.ui.viewport.topology_overlay import TopologyDensityOverlay
from opencae.ui.viewport.viewport_factory import create_viewport

from .topology_convergence_plot import TopologyConvergencePlot
from .topology_threshold_control import TopologyThresholdControl


class TopologyJobMonitor(QDialog):
    """Show the latest topology frame, convergence state, and solver transcript."""

    def __init__(self, store, job_id, parent=None):
        """Build a resizable visualization/output monitor for one Study Job."""
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
        self.resize(980, 760)
        self.setMinimumSize(720, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        self.phase = QLabel(getattr(job, "progress_label", "Prepared"))
        self.metrics = QLabel("Waiting for the first optimization iteration")
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        layout.addWidget(self.phase)
        layout.addWidget(self.metrics)
        layout.addWidget(self.progress)

        self.tabs = QTabWidget()
        density_page = QWidget()
        density_layout = QVBoxLayout(density_page)
        density_layout.setContentsMargins(8, 8, 8, 8)
        density_layout.setSpacing(8)

        self.threshold_control = TopologyThresholdControl()
        density_layout.addWidget(self.threshold_control)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.viewport = create_viewport(store, splitter)
        self.viewport.set_stage("STUDIES")
        self.viewport.set_display_mode("mesh")
        splitter.addWidget(self.viewport)

        output_host = QWidget(splitter)
        output_layout = QVBoxLayout(output_host)
        output_layout.setContentsMargins(0, 8, 0, 0)
        output_layout.setSpacing(8)
        output_layout.addWidget(SectionHeading("Solver Output"))
        self.output = MonospaceOutputView(output_host)
        output_layout.addWidget(self.output, 1)
        splitter.addWidget(output_host)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([500, 170])
        density_layout.addWidget(splitter, 1)
        self.tabs.addTab(density_page, "Density")

        self.convergence = TopologyConvergencePlot()
        self.tabs.addTab(self.convergence, "Convergence")
        layout.addWidget(self.tabs, 1)

        self.threshold_control.threshold_changed.connect(self._present_pending)

        self.viewport.request_refresh(fit=True)
        self.set_progress(
            self.job_id,
            getattr(job, "progress", 0.0),
            getattr(job, "progress_label", "Prepared"),
        )
        QTimer.singleShot(0, self._restore_latest_frame)

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

    def show_frame(self, job_id, run, iteration, mesh_index, density):
        """Queue the newest topology frame and convergence metrics for display."""
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
        try:
            _stored_density, volumes = load_density_state(iteration.density_file)
        except (OSError, KeyError, ValueError):
            volumes = None
        self.convergence.set_iterations(
            run.iterations,
            active_constraint_limit(self.store.project, run),
        )
        self._pending = (run, iteration, mesh_index, density, volumes)
        QTimer.singleShot(0, self._present_pending)

    def _restore_latest_frame(self):
        """Reload the latest persisted density frame when reopening a monitor."""
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
            density, _ = load_density_state(path)
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
        """Present only the most recent queued topology density frame."""
        if self._pending is None:
            return
        run, iteration, mesh_index, density, volumes = self._pending
        try:
            threshold = self.threshold_control.value
            if self.threshold_control.automatic:
                matched = automatic_density_threshold(
                    self.store.project,
                    run,
                    mesh_index,
                    density,
                    volumes,
                )
                if matched is not None:
                    threshold, achieved, limit = matched
                    self.threshold_control.show_automatic_result(
                        threshold,
                        achieved,
                        limit,
                        approximate=volumes is None,
                    )
                else:
                    threshold = 0.0
                    self.threshold_control.show_automatic_unavailable()
            else:
                self.threshold_control.show_manual_result()
            self.overlay.show(
                self.viewport,
                run,
                iteration,
                mesh_index,
                density,
                threshold=threshold,
            )
        except Exception as exc:
            self.phase.setText(f"Live visualization failed: {exc}")

    def closeEvent(self, event):
        """Release monitor-owned topology actors before destroying the viewport."""
        self.overlay.clear(self.viewport)
        super().closeEvent(event)
