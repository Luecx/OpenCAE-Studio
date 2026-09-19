"""Live mesh-convergence curves, level results and solver output for a Study Job."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QProgressBar, QSplitter, QTabWidget,
    QVBoxLayout, QWidget,
)

from opencae.model.entities.studies import MeshConvergenceStudy
from opencae.ui.core.widgets import MonospaceOutputView
from opencae.ui.panels.time_manager_plot import TimeManagerPlot
from opencae.ui.primitives.buttons import ButtonFormAction
from opencae.ui.templates import SectionHeading


class MeshConvergenceJobMonitor(QDialog):
    """Render every displacement control as it finishes, not only after the run."""

    def __init__(self, store, job_id, parent=None, *, stop_callback=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.store, self.job_id = store, str(job_id)
        self._stop_callback = stop_callback
        self._plots = {}
        self._measurements = {}
        job = store.project.try_resolve(self.job_id)
        self.setWindowTitle(f"Mesh Convergence — {getattr(job, 'name', 'Study')}")
        self.resize(980, 710)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)
        self.phase = QLabel(getattr(job, "progress_label", "Waiting"))
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        root.addWidget(self.phase)
        root.addWidget(self.progress)
        split = QSplitter(Qt.Orientation.Vertical)
        self.tabs = QTabWidget()
        split.addWidget(self.tabs)
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.addWidget(SectionHeading("Solver Output"))
        self.output = MonospaceOutputView()
        panel_layout.addWidget(self.output, 1)
        split.addWidget(panel)
        split.setStretchFactor(0, 4)
        split.setStretchFactor(1, 1)
        split.setSizes([480, 180])
        root.addWidget(split, 1)
        actions = QHBoxLayout()
        self.results = ButtonFormAction("Open Results")
        self.results.clicked.connect(self._open_results)
        self.stop_button = ButtonFormAction("Stop")
        self.stop_button.clicked.connect(self._stop)
        actions.addStretch(1)
        actions.addWidget(self.results)
        actions.addWidget(self.stop_button)
        root.addLayout(actions)
        self.store.changed.connect(self._refresh_results)
        self.set_progress(
            self.job_id, getattr(job, "progress", 0),
            getattr(job, "progress_label", "Prepared"),
        )
        self._restore_samples()
        self._refresh_results()

    def _restore_samples(self):
        job = self.store.project.try_resolve(self.job_id)
        study = self.store.project.try_resolve(getattr(job, "source_ref", None))
        if not isinstance(study, MeshConvergenceStudy):
            return
        for record in study.run_history:
            if record.get("job_id") == self.job_id:
                for sample in record.get("samples", ()):
                    self.sample_added(self.job_id, sample)
                return

    def sample_added(self, job_id, sample):
        """Append one completed level to every selected-node/global-max curve."""
        if str(job_id) != self.job_id:
            return
        for key, value in sample.get("metrics", {}).items():
            if key not in self._plots:
                plot = TimeManagerPlot()
                self._plots[key] = plot
                self._measurements[key] = []
                self.tabs.addTab(
                    plot, str(value.get("metric_name", key)),
                )
            series = self._measurements[key]
            series.append((float(sample["elements"]), float(value["value"])))
            self._plots[key].set_series(
                [x for x, _ in series], [y for _, y in series],
                x_label="Finite elements",
                y_label=f"{value.get('field', 'DISP')}: {value.get('component', 'Magnitude')}",
                show_markers=True, interactive=False,
                range_editable=False, show_play_range=False,
            )

    def set_progress(self, job_id, progress, label):
        if str(job_id) != self.job_id:
            return
        self.phase.setText(str(label))
        self.progress.setValue(
            round(min(max(float(progress), 0.0), 1.0) * 1000)
        )
        terminal = str(label).casefold() in {
            "completed", "failed", "cancelled", "stopping"
        }
        self.stop_button.setEnabled(
            callable(self._stop_callback) and not terminal
        )

    def set_output(self, job_id, output):
        if str(job_id) == self.job_id:
            self.output.set_output(output)

    def append_output(self, job_id, output):
        if str(job_id) == self.job_id:
            self.output.append_output(output)

    def _level_results(self):
        job = self.store.project.try_resolve(self.job_id)
        if job is None:
            return []
        return [
            result for reference in job.result_refs
            if (result := self.store.project.try_resolve(reference)) is not None
            and bool(result.source_file)
        ]

    def _refresh_results(self, *_):
        self.results.setEnabled(bool(self._level_results()))

    def _open_results(self, _checked=False):
        results = self._level_results()
        parent = self.parent()
        if results and callable(getattr(parent, "show_solution", None)):
            # Each level is a real ResultSet in the standard Results browser.
            # Display the last completed mesh and leave all levels accessible
            # from the left-hand solution tree.
            parent.show_solution(results[-1])
            self.hide()

    def _stop(self, _checked=False):
        if callable(self._stop_callback):
            self.stop_button.setEnabled(False)
            self._stop_callback()
