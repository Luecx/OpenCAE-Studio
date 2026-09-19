"""Mesh Convergence: grouped Study setup and independently editable controls."""
from __future__ import annotations

from copy import deepcopy
from csv import writer
from pathlib import Path
from uuid import uuid4

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QListWidget, QMessageBox, QTabWidget, QVBoxLayout,
    QWidget,
)

from opencae.model.core import EntityRef
from opencae.model.entities.studies import MeshConvergenceStudy
from opencae.model.selection import SelectableKind, SelectionOperation, SelectionPolicy
from opencae.results.mesh_convergence import METRICS, assess_convergence, assess_all_metrics
from opencae.ui.panels.time_manager_plot import TimeManagerPlot
from opencae.ui.primitives.buttons import ButtonFormAction
from opencae.ui.primitives.inputs import InputFormText
from opencae.ui.primitives.selects import SelectForm


def _coordinates(value):
    parts = [part.strip() for part in value.replace(";", ",").split(",")]
    if len(parts) != 3:
        raise ValueError("Coordinates require X, Y, Z separated by commas")
    return tuple(float(part) for part in parts)


class MeshConvergenceDialog(QDialog):
    """Modeless by design: users must be able to pick nodes in the viewport."""

    def __init__(self, project, study=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mesh Convergence Study")
        self.resize(790, 680)
        self.project = project
        self.viewport = getattr(parent, "viewport", None)
        self.original = deepcopy(study) if isinstance(study, MeshConvergenceStudy) else MeshConvergenceStudy(
            name=f"Mesh Convergence-{len(project.studies) + 1}"
        )
        self._metrics = deepcopy(self.original.metrics)
        self._editing_metric = -1
        self._picked_nodes = []
        self._pick_active = False
        self._candidate = None
        root = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs, 1)
        self._general_tab()
        self._metrics_tab()
        self._advanced_tab()
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self.finished.connect(lambda _code: self._stop_pick())
        self._refresh_metrics()

    def _general_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        group = QGroupBox("Study and solver")
        form = QFormLayout(group)
        value = self.original
        self.name = InputFormText(value.name)
        self.analysis = SelectForm()
        for analysis in self.project.analyses:
            self.analysis.addItem(analysis.name, analysis.id)
        selected = self.analysis.findData(value.analysis_ref.entity_id)
        if selected >= 0:
            self.analysis.setCurrentIndex(selected)
        self.scales = InputFormText(", ".join(f"{x:g}" for x in value.mesh_scales))
        self.scales.setPlaceholderText("1.0, 0.7, 0.5, 0.35")
        self.step = InputFormText(str(value.step_id))
        self.tolerance = InputFormText(f"{100 * value.relative_tolerance:g}")
        form.addRow("Study name", self.name)
        form.addRow("Analysis", self.analysis)
        form.addRow("Relative mesh-size factors", self.scales)
        form.addRow("Analysis Step ID", self.step)
        form.addRow("Tolerance (%)", self.tolerance)
        layout.addWidget(group)
        note = QLabel(
            "Each level remeshes the CAD Parts and runs the same Analysis. "
            "Define one or more independent monitoring metrics under Metrics. "
            "Node IDs change between refinements: selected mesh nodes are stored "
            "as physical positions and re-evaluated there at every level."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        self.tabs.addTab(tab, "General")

    def _metrics_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        group = QGroupBox("Convergence controls")
        group_layout = QVBoxLayout(group)
        self.metric_list = QListWidget()
        self.metric_list.setMinimumHeight(110)
        group_layout.addWidget(self.metric_list)
        row = QHBoxLayout()
        add_displacement = ButtonFormAction("Add displacement control")
        add_field = ButtonFormAction("Add field metric")
        remove = ButtonFormAction("Remove")
        row.addWidget(add_displacement)
        row.addWidget(add_field)
        row.addWidget(remove)
        group_layout.addLayout(row)
        layout.addWidget(group)
        editor_group = QGroupBox("Selected metric")
        form = QFormLayout(editor_group)
        self.metric_name = InputFormText()
        self.metric_kind = SelectForm()
        self.metric_kind.addItem("Displacement control — selected nodes", "displacement_control")
        self.metric_kind.addItem("Field at fixed position", "probe")
        self.metric_kind.addItem("Measure-weighted RMS", "weighted_rms")
        self.metric_kind.addItem("Measure-weighted 95th percentile", "weighted_p95")
        self.metric_kind.addItem("Global nodal maximum (diagnostic only)", "nodal_max")
        self.metric_field = InputFormText("DISP")
        self.metric_component = SelectForm()
        for name in ("Magnitude", "D1", "D2", "D3", "Mises", "S11", "S22", "S33", "S12"):
            self.metric_component.addItem(name, name)
        self.metric_component.setEditable(True)
        self.metric_position = InputFormText("0, 0, 0")
        self.metric_nodes = QListWidget()
        self.metric_nodes.setMaximumHeight(105)
        self.pick_nodes = ButtonFormAction("Pick nodes in viewport")
        self.remove_node = ButtonFormAction("Remove selected node")
        self.update_metric = ButtonFormAction("Apply metric changes")
        form.addRow("Name", self.metric_name)
        form.addRow("Measurement", self.metric_kind)
        form.addRow("FRD field", self.metric_field)
        form.addRow("Component", self.metric_component)
        form.addRow("Probe X, Y, Z", self.metric_position)
        form.addRow("Selected original mesh nodes", self.metric_nodes)
        controls = QHBoxLayout()
        controls.addWidget(self.pick_nodes)
        controls.addWidget(self.remove_node)
        form.addRow("", controls)
        form.addRow("", self.update_metric)
        layout.addWidget(editor_group)
        self.metric_list.currentRowChanged.connect(self._select_metric)
        self.metric_kind.currentIndexChanged.connect(self._metric_kind_changed)
        add_displacement.clicked.connect(lambda _checked=False: self._add_metric("displacement_control"))
        add_field.clicked.connect(lambda _checked=False: self._add_metric("probe"))
        remove.clicked.connect(self._remove_metric)
        self.pick_nodes.clicked.connect(self._begin_node_pick)
        self.remove_node.clicked.connect(self._remove_node)
        self.update_metric.clicked.connect(self._commit_metric)
        self.tabs.addTab(tab, "Metrics")

    def _advanced_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        group = QGroupBox("Singularity exclusion (optional)")
        form = QFormLayout(group)
        value = self.original
        self.exclude_center = InputFormText(
            ", ".join(f"{x:g}" for x in value.exclude_center)
        )
        self.exclude_radius = InputFormText(f"{value.exclude_radius:g}")
        form.addRow("Exclusion center X, Y, Z", self.exclude_center)
        form.addRow("Exclusion radius (model units)", self.exclude_radius)
        layout.addWidget(group)
        note = QLabel(
            "A singularity zone excludes probes and regional samples within "
            "its radius. A global peak is always diagnostic, even when outside "
            "the exclusion zone. No metric trend certifies an FE error bound."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        self.tabs.addTab(tab, "Advanced")

    def _refresh_metrics(self, row=None):
        self.metric_list.blockSignals(True)
        self.metric_list.clear()
        for item in self._metrics:
            count = len(item.get("nodes", ()))
            suffix = f" · {count} nodes" if item.get("kind") == "displacement_control" else ""
            self.metric_list.addItem(f"{item.get('name', 'Metric')} — {item.get('kind')}{suffix}")
        if self._metrics:
            self.metric_list.setCurrentRow(min(
                max(0, self._editing_metric if row is None else row),
                len(self._metrics)-1,
            ))
        self.metric_list.blockSignals(False)
        self._select_metric(self.metric_list.currentRow())

    def _add_metric(self, kind):
        self._stop_pick()
        existing = {item.get("name") for item in self._metrics}
        base = "Displacement control" if kind == "displacement_control" else "Field metric"
        name = base
        suffix = 2
        while name in existing:
            name = f"{base} {suffix}"
            suffix += 1
        self._metrics.append(dict(
            id=uuid4().hex, kind=kind, metric=kind if kind != "displacement_control" else "probe",
            name=name, field_name="DISP" if kind == "displacement_control" else "STRESS",
            component="Magnitude" if kind == "displacement_control" else "Mises",
            probe_position=[0.0, 0.0, 0.0], nodes=[],
        ))
        self._refresh_metrics(len(self._metrics)-1)

    def _save_editor_draft(self):
        """Preserve edits, including picked nodes, when switching controls."""
        index = self._editing_metric
        if index < 0 or index >= len(self._metrics):
            return
        current = self._metrics[index]
        current["name"] = self.metric_name.text().strip()
        current["kind"] = self.metric_kind.currentData()
        current["component"] = self.metric_component.currentText().strip()
        current["field_name"] = (
            "DISP" if current["kind"] == "displacement_control"
            else self.metric_field.text().strip()
        )
        current["metric"] = (
            "probe" if current["kind"] == "displacement_control"
            else current["kind"]
        )
        current["nodes"] = deepcopy(self._picked_nodes)
        # Preserve text until final validation; do not lose edits on tab change.
        try:
            current["probe_position"] = list(_coordinates(self.metric_position.text()))
        except (ValueError, TypeError):
            current["probe_position"] = list(current.get("probe_position", (0, 0, 0)))

    def _select_metric(self, index):
        if index != self._editing_metric:
            self._save_editor_draft()
        self._stop_pick()
        self._editing_metric = index
        if index < 0 or index >= len(self._metrics):
            self._picked_nodes = []
            self.metric_nodes.clear()
            return
        metric = self._metrics[index]
        self.metric_name.setText(metric["name"])
        self.metric_kind.setCurrentIndex(max(0, self.metric_kind.findData(metric["kind"])))
        self.metric_field.setText(metric.get("field_name", "DISP"))
        self.metric_component.setCurrentText(metric.get("component", "Magnitude"))
        self.metric_position.setText(
            ", ".join(f"{x:g}" for x in metric.get("probe_position", (0, 0, 0)))
        )
        self._picked_nodes = deepcopy(metric.get("nodes", ()))
        self._refresh_nodes()
        self._metric_kind_changed()

    def _metric_kind_changed(self, *_):
        is_displacement = self.metric_kind.currentData() == "displacement_control"
        self.metric_nodes.setEnabled(is_displacement)
        self.pick_nodes.setEnabled(is_displacement)
        self.remove_node.setEnabled(is_displacement)
        self.metric_position.setEnabled(self.metric_kind.currentData() == "probe")
        self.metric_field.setEnabled(not is_displacement)
        if is_displacement:
            self.metric_field.setText("DISP")

    def _refresh_nodes(self):
        self.metric_nodes.clear()
        for node in self._picked_nodes:
            xyz = ", ".join(f"{float(x):.6g}" for x in node["position"])
            self.metric_nodes.addItem(
                f"Node {node['node_id']} · {node.get('instance_name', 'Part')} · ({xyz})"
            )

    def _begin_node_pick(self, _checked=False):
        if self.viewport is None:
            QMessageBox.warning(self, "Select nodes", "No active viewport is available")
            return
        if self._editing_metric < 0 or self.metric_kind.currentData() != "displacement_control":
            return
        if not any(getattr(part.mesh, "node_count", 0) for part in self.project.parts):
            QMessageBox.warning(
                self, "Select nodes",
                "Generate a mesh first. The picker uses nodes from the "
                "original model and stores their physical positions for refinement.",
            )
            return
        self.viewport.set_display_mode("mesh")
        policy = SelectionPolicy.create({SelectableKind.MESH_NODE}, multiple=True)

        def received(hit):
            if hit.kind is not SelectableKind.MESH_NODE or hit.mesh_id is None or hit.world_position is None:
                return
            # A normal click must append another monitoring node. Only the
            # explicit Remove button or Ctrl-click removes a selected node.
            key = (str(hit.instance_id or ""), int(hit.mesh_id))
            self._picked_nodes = [
                item for item in self._picked_nodes
                if (item.get("instance_id", ""), int(item["node_id"])) != key
            ]
            if hit.selection_operation is not SelectionOperation.REMOVE:
                self._picked_nodes.append(dict(
                    node_id=int(hit.mesh_id),
                    instance_id=str(hit.instance_id or ""),
                    instance_name=str(hit.label).split(".Node-")[0] if ".Node-" in str(hit.label) else "Part",
                    position=list(map(float, hit.world_position)),
                ))
            self._refresh_nodes()

        self._pick_active = True
        self.viewport.begin_selection_session(policy, received, finished=self._pick_finished)
        self.pick_nodes.setText("Picking nodes — click to stop")
        self.pick_nodes.clicked.disconnect(self._begin_node_pick)
        self.pick_nodes.clicked.connect(self._stop_pick)

    def _pick_finished(self):
        self._pick_active = False
        try:
            self.pick_nodes.clicked.disconnect(self._stop_pick)
        except (TypeError, RuntimeError):
            pass
        self.pick_nodes.clicked.connect(self._begin_node_pick)
        self.pick_nodes.setText("Pick nodes in viewport")

    def _stop_pick(self, *_):
        if self._pick_active and self.viewport is not None:
            self.viewport.cancel_context_pick()

    def _remove_node(self, _checked=False):
        row = self.metric_nodes.currentRow()
        if 0 <= row < len(self._picked_nodes):
            del self._picked_nodes[row]
            self._refresh_nodes()

    def _remove_metric(self, _checked=False):
        index = self._editing_metric
        if index < 0:
            return
        self._stop_pick()
        del self._metrics[index]
        self._editing_metric = min(index, len(self._metrics)-1)
        self._refresh_metrics()

    def _commit_metric(self, _checked=False):
        index = self._editing_metric
        if index < 0:
            return
        try:
            candidate = deepcopy(self._metrics[index])
            candidate["name"] = self.metric_name.text().strip()
            candidate["kind"] = self.metric_kind.currentData()
            candidate["component"] = self.metric_component.currentText().strip()
            candidate["field_name"] = (
                "DISP" if candidate["kind"] == "displacement_control"
                else self.metric_field.text().strip()
            )
            candidate["metric"] = (
                "probe" if candidate["kind"] == "displacement_control"
                else candidate["kind"]
            )
            candidate["probe_position"] = list(_coordinates(self.metric_position.text()))
            candidate["nodes"] = deepcopy(self._picked_nodes)
            if not candidate["name"] or not candidate["component"] or not candidate["field_name"]:
                raise ValueError("Metric name, field and component must not be empty")
            if candidate["kind"] == "displacement_control" and not candidate["nodes"]:
                raise ValueError("Pick at least one mesh node for this displacement control")
            if any(i != index and m["name"] == candidate["name"]
                   for i,m in enumerate(self._metrics)):
                raise ValueError("Metric names must be unique")
            self._metrics[index] = candidate
            self._stop_pick()
            self._refresh_metrics(index)
        except (ValueError, TypeError) as exc:
            QMessageBox.warning(self, "Invalid metric", str(exc))
            return False
        return True

    def values(self):
        if self._editing_metric >= 0 and not self._commit_metric():
            raise ValueError("Correct the selected metric before saving")
        value = deepcopy(self.original)
        value.name = self.name.text().strip()
        if not value.name:
            raise ValueError("Study name must not be empty")
        analysis = self.project.try_resolve(self.analysis.currentData())
        if analysis is None:
            raise ValueError("Select an Analysis")
        value.analysis_ref = EntityRef.of(analysis, "Analysis")
        scales = [float(part.strip()) for part in
                  self.scales.text().replace(";", ",").split(",") if part.strip()]
        if len(scales) < 3 or any(x <= 0 for x in scales) or any(
            a <= b for a,b in zip(scales, scales[1:])
        ):
            raise ValueError("Enter at least three strictly decreasing positive mesh scales")
        value.mesh_scales = scales
        value.step_id = int(self.step.text())
        if value.step_id < 1:
            raise ValueError("Step ID must be positive")
        value.relative_tolerance = float(self.tolerance.text()) / 100.
        if not 0 < value.relative_tolerance < 1:
            raise ValueError("Tolerance must be between 0 and 100 percent")
        value.exclude_center = _coordinates(self.exclude_center.text())
        value.exclude_radius = float(self.exclude_radius.text())
        if value.exclude_radius < 0:
            raise ValueError("Exclusion radius must be nonnegative")
        if not self._metrics:
            raise ValueError("Add at least one convergence metric on the Metrics tab")
        for metric in self._metrics:
            if metric["kind"] == "displacement_control" and not metric.get("nodes"):
                raise ValueError(f"Pick at least one node for {metric['name']}")
        value.metrics = deepcopy(self._metrics)
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
        self.series = SelectForm()
        root.addWidget(self.series)
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
        self.runs.currentIndexChanged.connect(self._refresh_series)
        self.series.currentIndexChanged.connect(self._display)
        export.clicked.connect(self._export)
        close.clicked.connect(self.accept)
        self._refresh_series()

    def _refresh_series(self, *_):
        current = self.series.currentData()
        self.series.blockSignals(True)
        self.series.clear()
        run = self.runs.currentData() or {}
        samples = list(run.get("samples", ()))
        if samples:
            for key, value in samples[0].get("metrics", {}).items():
                self.series.addItem(value.get("metric_name", key), key)
            if not self.series.count():
                self.series.addItem("Legacy metric", "__legacy__")
        index = self.series.findData(current)
        self.series.setCurrentIndex(max(0, index))
        self.series.blockSignals(False)
        self._display()

    def _display(self, *_):
        run = self.runs.currentData() or {}
        samples = list(run.get("samples", ()))
        if not samples:
            self.chart.set_series([], [], show_play_range=False)
            self.diagnostics.setText("No completed refinement samples in this run.")
            return
        key = self.series.currentData()
        values = [
            sample if key == "__legacy__" else sample.get("metrics", {}).get(key)
            for sample in samples
        ]
        complete = [(sample, value) for sample, value in zip(samples, values)
                    if value is not None]
        if not complete:
            self.chart.set_series([], [], show_play_range=False)
            self.diagnostics.setText("No valid samples for the selected metric")
            return
        self.chart.set_series(
            [sample["elements"] for sample, _ in complete],
            [value["value"] for _, value in complete],
            x_label="Number of finite elements",
            y_label=f"{complete[0][1]['field']}: {complete[0][1]['component']}",
            show_markers=True, interactive=False, show_play_range=False,
        )
        selected = complete[0][1]
        conclusion = assess_all_metrics(
            samples, float(run.get("relative_tolerance", .02))
        ).get(key)
        if conclusion is None:
            conclusion = assess_convergence(
                [value for _, value in complete],
                float(run.get("relative_tolerance", .02)),
                selected.get("metric", "nodal_max"),
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
                    measurements = list(sample.get("metrics", {}).values()) or [sample]
                    for measurement in measurements:
                        output.writerow((
                            sample.get("level", ""), sample.get("seed_scale", ""),
                            sample.get("elements", ""), sample.get("nodes", ""),
                            measurement.get("metric_name", measurement.get("metric", "")),
                            measurement.get("field", ""), measurement.get("component", ""),
                            measurement.get("value", ""), sample.get("source_file", ""),
                        ))
        except OSError as exc:
            QMessageBox.warning(self, "Export CSV", str(exc))
