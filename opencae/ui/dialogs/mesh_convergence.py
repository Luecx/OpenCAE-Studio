"""Definition and analysis of an automatic Mesh Convergence Study."""
from __future__ import annotations
from copy import deepcopy
from csv import writer
from pathlib import Path

from opencae.ui.primitives.inputs import InputFormText
from opencae.ui.primitives.selects import SelectForm
from opencae.ui.primitives.buttons import ButtonFormAction

from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QMessageBox,
    QVBoxLayout,
)
from opencae.model.core import EntityRef
from opencae.model.entities.studies import MeshConvergenceStudy
from opencae.results.mesh_convergence import METRICS, assess_convergence
from opencae.ui.panels.time_manager_plot import TimeManagerPlot


def _coordinates(value):
    parts = [part.strip() for part in value.replace(";", ",").split(",")]
    if len(parts) != 3:
        raise ValueError("Coordinates require X, Y, Z separated by commas")
    return tuple(float(part) for part in parts)


class MeshConvergenceDialog(QDialog):
    def __init__(self, project, study=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mesh Convergence Study")
        self.resize(580, 420)
        self.project = project
        self.original = deepcopy(study) if study else MeshConvergenceStudy(
            name=f"Mesh Convergence-{len(project.studies) + 1}"
        )
        value = self.original
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.name = InputFormText(value.name)
        self.analysis = SelectForm()
        for item in project.analyses:
            self.analysis.addItem(item.name, item.id)
        chosen = self.analysis.findData(value.analysis_ref.entity_id)
        if chosen >= 0:
            self.analysis.setCurrentIndex(chosen)
        self.scales = InputFormText(", ".join(f"{x:g}" for x in value.mesh_scales))
        self.scales.setToolTip(
            "Scale factors applied to all CAD mesh-size seeds. "
            "Example 1, 0.7, 0.5, 0.35. Ordered coarse to fine."
        )
        self.field = InputFormText(value.field_name)
        self.component = InputFormText(value.component)
        self.step = InputFormText(str(value.step_id))
        self.metric = SelectForm()
        for key, label in METRICS.items():
            self.metric.addItem(label, key)
        index = self.metric.findData(value.metric)
        if index >= 0:
            self.metric.setCurrentIndex(index)
        self.position = InputFormText(", ".join(f"{x:g}" for x in value.probe_position))
        self.exclude_center = InputFormText(
            ", ".join(f"{x:g}" for x in value.exclude_center)
        )
        self.exclude_radius = InputFormText(f"{value.exclude_radius:g}")
        self.tolerance = InputFormText(f"{100*value.relative_tolerance:g}")
        for label, widget in (
            ("Study name", self.name), ("Analysis", self.analysis),
            ("Mesh-size scales", self.scales), ("FRD field (Y)", self.field),
            ("Component (Y)", self.component), ("Step ID", self.step),
            ("Convergence metric", self.metric), ("Probe position X, Y, Z", self.position),
            ("Singularity exclusion center", self.exclude_center),
            ("Exclusion radius (model units)", self.exclude_radius),
            ("Relative tolerance (%)", self.tolerance),
        ):
            form.addRow(label, widget)
        root.addLayout(form)
        info = QLabel(
            "Every level independently remeshes all CAD Parts and runs the chosen "
            "Analysis. A fixed-position probe and measure-weighted regional "
            "statistics can be compared across changing node IDs. A nodal maximum "
            "is diagnostic only and never qualifies as proof of convergence. "
            "An exclusion radius removes cells/points near a known singularity."
        )
        info.setWordWrap(True)
        root.addWidget(info)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def values(self):
        value = deepcopy(self.original)
        value.name = self.name.text().strip()
        if not value.name:
            raise ValueError("Study name must not be empty")
        selected = self.project.try_resolve(self.analysis.currentData())
        if selected is None:
            raise ValueError("Select an Analysis")
        value.analysis_ref = EntityRef.of(selected, "Analysis")
        scales = [float(item.strip()) for item in
                  self.scales.text().replace(";", ",").split(",") if item.strip()]
        if len(scales) < 3 or any(item <= 0 for item in scales):
            raise ValueError("Enter at least three positive mesh-size factors")
        if any(a <= b for a, b in zip(scales, scales[1:])):
            raise ValueError("Mesh-size factors must decrease strictly")
        value.mesh_scales = scales
        value.field_name = self.field.text().strip()
        value.component = self.component.text().strip()
        if not value.field_name or not value.component:
            raise ValueError("Specify an FRD field and component")
        value.step_id = int(self.step.text().strip())
        if value.step_id <= 0:
            raise ValueError("Step ID must be positive")
        value.metric = self.metric.currentData()
        value.probe_position = _coordinates(self.position.text())
        value.exclude_center = _coordinates(self.exclude_center.text())
        value.exclude_radius = float(self.exclude_radius.text())
        value.relative_tolerance = float(self.tolerance.text()) / 100.0
        if value.exclude_radius < 0:
            raise ValueError("Exclusion radius must be nonnegative")
        if not 0 < value.relative_tolerance < 1:
            raise ValueError("Tolerance must be between 0 and 100 percent")
        return value

    def _accept(self):
        try:
            self._candidate = self.values()
        except (TypeError, ValueError) as exc:
            QMessageBox.warning(self, "Invalid convergence definition", str(exc))
            return
        self.accept()

    def study(self):
        return self._candidate


class ConvergenceReportDialog(QDialog):
    """Render the persisted metric trend, diagnostics and individual FRD paths."""

    def __init__(self, study, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Mesh Convergence — {study.name}")
        self.resize(800, 510)
        root = QVBoxLayout(self)
        history = list(study.run_history or ())
        self.runs = SelectForm()
        for run in history:
            self.runs.addItem(
                f"{run.get('started_at', 'Run')} — {run.get('status', 'Unknown')}",
                run
            )
        root.addWidget(self.runs)
        self.chart = TimeManagerPlot()
        self.chart.setMinimumHeight(250)
        root.addWidget(self.chart, 1)
        self.diagnostics = QLabel()
        self.diagnostics.setWordWrap(True)
        root.addWidget(self.diagnostics)
        export = ButtonFormAction("Export CSV")
        close = ButtonFormAction("Close")
        buttons = QHBoxLayout()
        buttons.addWidget(export)
        buttons.addStretch(1)
        buttons.addWidget(close)
        root.addLayout(buttons)
        self.runs.currentIndexChanged.connect(self._display)
        export.clicked.connect(self._export)
        close.clicked.connect(self.accept)
        self._display()

    def _display(self, *_):
        run = self.runs.currentData() or {}
        samples = list(run.get("samples", ()))
        if not samples:
            self.chart.set_series([], [], show_play_range=False)
            self.diagnostics.setText("No completed refinement samples in this run.")
            return
        self.chart.set_series(
            [item["elements"] for item in samples],
            [item["value"] for item in samples],
            x_label="Number of finite elements",
            y_label=f"{samples[0]['field']}: {samples[0]['component']}",
            show_markers=True, interactive=False, show_play_range=False,
        )
        conclusion = assess_convergence(
            samples, float(run.get("relative_tolerance", .02)),
            run.get("metric", "nodal_max")
        )
        self.diagnostics.setText(
            f"Status: {run.get('status', 'Unknown')} — {conclusion}\n"
            f"Exclusion radius: {run.get('exclude_radius', 0):g} | "
            f"Completed levels: {len(samples)}. "
            "This is a metric trend, not a certified numerical error estimate. "
            "Use the associated FRD files to inspect localized peaks."
        )

    def _export(self):
        run = self.runs.currentData() or {}
        samples = run.get("samples", ())
        if not samples:
            return
        name, _ = QFileDialog.getSaveFileName(
            self, "Export convergence data", "mesh-convergence.csv",
            "CSV files (*.csv)"
        )
        if not name:
            return
        try:
            with Path(name).with_suffix(".csv").open(
                "w", newline="", encoding="utf-8"
            ) as handle:
                output = writer(handle)
                output.writerow((
                    "Level", "Seed scale", "Elements", "Nodes",
                    "Metric", "Field", "Component", "Value",
                    "Source FRD",
                ))
                for sample in samples:
                    output.writerow(tuple(sample.get(key, "") for key in (
                        "level", "seed_scale", "elements", "nodes", "metric",
                        "field", "component", "value", "source_file",
                    )))
        except OSError as exc:
            QMessageBox.warning(self, "Export CSV", str(exc))
