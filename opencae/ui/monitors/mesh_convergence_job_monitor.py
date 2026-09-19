"""Theme-aligned live convergence monitor using the shared Time Manager plot."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QProgressBar, QSplitter,
    QVBoxLayout, QWidget,
)

from opencae.model.entities.studies import MeshConvergenceStudy
from opencae.ui.core.widgets import MonospaceOutputView
from opencae.ui.panels.time_manager_plot import TimeManagerPlot
from opencae.ui.primitives.buttons import ButtonFormAction
from opencae.ui.primitives.checks import CheckForm
from opencae.ui.primitives.selects import SelectForm
from opencae.ui.templates import SectionHeading, field_block


_X_FIELDS = {
    "nodes": ("nodes", "Nodes"),
    "elements": ("elements", "Elements"),
    "level": ("level", "Level"),
}


class MeshConvergenceJobMonitor(QDialog):
    """Show one consistently themed plot with selectable monitoring node and X axis."""

    def __init__(self, store, job_id, parent=None, *, stop_callback=None):
        super().__init__(parent)
        self.setObjectName("MeshConvergenceJobMonitor")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.store, self.job_id = store, str(job_id)
        self._stop_callback = stop_callback
        # Keep original per-level quantities. Axis changes must never rebuild
        # a series from previously transformed coordinates or drop raw samples.
        self._measurements = {}
        self._labels = {}
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
        # Transparent layout surface: use the dialog's window background
        # instead of the brighter panel color used by docked Time Manager.
        self.plot_surface = QWidget()
        plot_layout = QVBoxLayout(self.plot_surface)
        plot_layout.setContentsMargins(12, 10, 12, 8)
        plot_layout.setSpacing(8)
        plot_layout.addWidget(SectionHeading("Convergence"))
        options = QHBoxLayout()
        options.setSpacing(12)
        self.series = SelectForm()
        self.series.setMinimumWidth(220)
        options.addWidget(field_block("Metric / monitored node", self.series), 2)
        self.x_axis = SelectForm()
        for key, (_field, label) in _X_FIELDS.items():
            self.x_axis.addItem(label, key)
        self.x_axis.setCurrentIndex(self.x_axis.findData("elements"))
        options.addWidget(field_block("X axis", self.x_axis), 1)
        self.log_x = CheckForm("Logarithmic X axis")
        self.log_x.setToolTip(
            "Use base-10 logarithmic spacing for the selected X axis. "
            "Original node counts, element counts and level numbers stay unchanged."
        )
        options.addWidget(self.log_x, 0, Qt.AlignmentFlag.AlignBottom)
        plot_layout.addLayout(options)
        self.plot = TimeManagerPlot(self.plot_surface, background_role="window")
        self.plot.setMinimumHeight(260)
        plot_layout.addWidget(self.plot, 1)
        self.readout = QLabel("No completed mesh levels yet")
        self.readout.setWordWrap(True)
        plot_layout.addWidget(self.readout)
        split.addWidget(self.plot_surface)

        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 8, 12, 8)
        panel_layout.addWidget(SectionHeading("Solver Output"))
        self.output = MonospaceOutputView()
        self.output.setObjectName("MeshConvergenceOutput")
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
        self.series.currentIndexChanged.connect(self._redraw)
        self.x_axis.currentIndexChanged.connect(self._redraw)
        self.log_x.toggled.connect(self._redraw)
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
        """Append every level's raw counts and measurements, including live points."""
        if str(job_id) != self.job_id:
            return
        for key, value in sample.get("metrics", {}).items():
            if key not in self._measurements:
                self._measurements[key] = []
                self._labels[key] = str(value.get("metric_name", key))
                self.series.addItem(self._labels[key], key)
            self._measurements[key].append({
                "level": int(sample["level"]),
                "nodes": int(sample["nodes"]),
                "elements": int(sample["elements"]),
                "value": float(value["value"]),
                "field": str(value.get("field", "DISP")),
                "component": str(value.get("component", "Magnitude")),
            })
        self._redraw()

    def _redraw(self, *_):
        key = self.series.currentData()
        measurements = self._measurements.get(key, ())
        axis = self.x_axis.currentData() or "elements"
        field, label = _X_FIELDS.get(axis, _X_FIELDS["elements"])
        if not measurements:
            self.plot.set_series([], [], x_label=label, y_label="Displacement",
                                 interactive=False, show_play_range=False)
            self.readout.setText("No completed mesh levels yet")
            return
        scale = "log" if self.log_x.isChecked() else "linear"
        x = [entry[field] for entry in measurements]
        y = [entry["value"] for entry in measurements]
        self.plot.set_series(
            x, y,
            x_label=label,
            y_label=f"{measurements[-1]['field']}: {measurements[-1]['component']}",
            x_scale=scale, point_value_labels=True, show_markers=True,
            interactive=False, range_editable=False, show_play_range=False,
        )
        last = measurements[-1]
        self.readout.setText(
            f"Level {last['level']} · {last['nodes']:,} nodes · "
            f"{last['elements']:,} elements · "
            f"{self._labels.get(key, 'Displacement')}: {last['value']:.9g}"
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
            parent.show_solution(results[-1])
            self.hide()

    def _stop(self, _checked=False):
        if callable(self._stop_callback):
            self.stop_button.setEnabled(False)
            self._stop_callback()
