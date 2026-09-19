"""Canonical OpenCAE form for displacement-only mesh-convergence studies."""
from __future__ import annotations

from copy import deepcopy
from csv import writer
from pathlib import Path
from uuid import uuid4

from PyQt6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QMessageBox, QVBoxLayout, QWidget, QLabel,
)

from opencae.controllers.region_selection import begin_region_pick
from opencae.model.core import EntityRef
from opencae.model.entities.studies import MeshConvergenceStudy
from opencae.model.selection import (
    MeshNodeOperand, RegionDefinition, RegionSelectionItem,
    SelectableKind, SelectionOperation, SelectionPolicy,
)
from opencae.results.mesh_convergence import assess_convergence, assess_all_metrics
from opencae.ui.core.widgets import CompactRegionSelector, ReferenceSelector
from opencae.ui.panels.time_manager_plot import TimeManagerPlot
from opencae.ui.primitives.buttons import ButtonFormAction
from opencae.ui.primitives.inputs import InputFormText
from opencae.ui.primitives.lists import ListForm
from opencae.ui.primitives.selects import SelectForm
from opencae.ui.templates import (
    SectionHeading, dialog_buttons, dialog_layout, field_block, field_row,
)


_DISPLACEMENT_COMPONENTS = ("Magnitude", "D1", "D2", "D3", "D4", "D5", "D6")


def _nodes_from_definition(definition):
    values = []
    for item in definition.items:
        operand = item.operand
        if not isinstance(operand, MeshNodeOperand):
            continue
        if item.picked_position is None:
            raise ValueError("Selected node has no original spatial position")
        values.append({
            "node_id": operand.node_id,
            "owner_id": operand.owner_ref.entity_id,
            "instance_id": operand.instance_ref.entity_id if operand.instance_ref else "",
            "position": list(item.picked_position),
            "label": item.display_label or f"Node-{operand.node_id}",
        })
    return values


def _node_definition(nodes):
    result = []
    for node in nodes:
        owner = str(node.get("owner_id", ""))
        if not owner or len(node.get("position", ())) != 3:
            continue
        from opencae.model.core import EntityRef
        instance = str(node.get("instance_id", ""))
        result.append(RegionSelectionItem(
            MeshNodeOperand(
                EntityRef(owner, "Part"),
                int(node["node_id"]),
                EntityRef(instance, "Instance") if instance else None,
            ),
            tuple(node["position"]),
            str(node.get("label", f"Node-{node['node_id']}")),
        ))
    return RegionDefinition(tuple(result))


class MeshConvergenceDialog(QDialog):
    """The same field-block/region-picker system as Topology Optimization."""

    def __init__(self, project, study=None, parent=None):
        super().__init__(parent)
        self.project = project
        self.viewport = getattr(parent, "viewport", None)
        self.original = deepcopy(study) if isinstance(study, MeshConvergenceStudy) else MeshConvergenceStudy(
            name=f"Mesh Convergence-{len(project.studies) + 1}"
        )
        self._metrics = deepcopy(self.original.metrics)
        self._editing_metric = -1
        self._candidate = None
        self.setWindowTitle("Mesh Convergence Study")
        self.setMinimumWidth(660)
        self.resize(730, 700)
        root = dialog_layout(self)

        self.name = InputFormText(self.original.name)
        root.addWidget(field_block("Name", self.name))
        self.analysis = ReferenceSelector(
            [(item.name, item.id) for item in project.analyses],
            self.original.analysis_ref.entity_id,
        )
        root.addWidget(field_block("Analysis", self.analysis))
        self.scales = InputFormText(
            ", ".join(f"{number:g}" for number in self.original.mesh_scales)
        )
        root.addWidget(field_block("Relative mesh-size factors", self.scales))
        self.step = InputFormText(str(self.original.step_id))
        self.tolerance = InputFormText(f"{100 * self.original.relative_tolerance:g}")
        root.addWidget(field_row(
            field_block("Step ID", self.step),
            field_block("Tolerance (%)", self.tolerance),
        ))
        root.addWidget(SectionHeading("Displacement Controls"))
        self.metric_list = ListForm(minimum_height=90)
        self.metric_list.setMaximumHeight(150)
        root.addWidget(self.metric_list)
        controls = QHBoxLayout()
        add = ButtonFormAction("Add displacement control")
        remove = ButtonFormAction("Remove control")
        controls.addWidget(add)
        controls.addWidget(remove)
        controls.addStretch(1)
        root.addLayout(controls)

        # Do not show a phantom Selected Metric form when no controls exist.
        self.editor = QWidget(self)
        editor_layout = QVBoxLayout(self.editor)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addWidget(SectionHeading("Selected Displacement Control"))
        self.metric_name = InputFormText()
        editor_layout.addWidget(field_block("Name", self.metric_name))
        self.component = SelectForm()
        for name in _DISPLACEMENT_COMPONENTS:
            self.component.addItem(name, name)
        editor_layout.addWidget(field_block("Component", self.component))
        self.nodes = CompactRegionSelector(
            project, pick_callback=self._pick_nodes,
            options=(), show_extended=False, parent=self.editor,
        )
        editor_layout.addWidget(field_block("Monitor nodes", self.nodes))
        self.hint = QLabel(
            "Without selected nodes, this control evaluates the global "
            "displacement maximum. Selected nodes are tracked at their "
            "physical positions on each refined mesh.",
        )
        self.hint.setWordWrap(True)
        editor_layout.addWidget(self.hint)
        root.addWidget(self.editor)
        root.addStretch(1)
        buttons = dialog_buttons()
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        add.clicked.connect(self._add)
        remove.clicked.connect(self._remove)
        self.metric_list.currentRowChanged.connect(self._selected)
        self.finished.connect(lambda _code: self.nodes.finish_pick())
        self._refresh()

    def _pick_nodes(self, _widget, done, finished):
        if self.viewport is None:
            QMessageBox.warning(self, "Select nodes", "No active viewport is available")
            return None
        if not any(part.mesh.node_count for part in self.project.parts):
            QMessageBox.warning(self, "Select nodes", "Generate the mesh before selecting monitor nodes")
            return None
        self.viewport.set_display_mode("mesh")
        policy = SelectionPolicy.create({SelectableKind.MESH_NODE}, multiple=True)
        default_owner = self.project.parts[0] if len(self.project.parts) == 1 else None

        def selected(definition, operation):
            # Each plain click adds a control node. Ctrl-click removes it.
            done(definition, SelectionOperation.REMOVE
                 if operation == SelectionOperation.REMOVE
                 else SelectionOperation.ADD)

        return begin_region_pick(
            self.project, self.viewport, policy, selected,
            default_owner=default_owner, finished=finished,
        )

    def _sync_editor(self):
        index = self._editing_metric
        if index < 0 or index >= len(self._metrics):
            return
        current = self._metrics[index]
        current["name"] = self.metric_name.text().strip()
        current["component"] = str(self.component.currentData() or "Magnitude")
        current["nodes"] = _nodes_from_definition(self.nodes.definition())

    def _refresh(self, selected=None):
        self.metric_list.blockSignals(True)
        self.metric_list.clear()
        for spec in self._metrics:
            quantity = len(spec.get("nodes", ()))
            label = f"{spec.get('name', 'Displacement')} · "
            label += f"{quantity} nodes" if quantity else "Global maximum"
            self.metric_list.addItem(label)
        if self._metrics:
            self.metric_list.setCurrentRow(
                min(max(0, self._editing_metric if selected is None else selected),
                    len(self._metrics) - 1)
            )
        self.metric_list.blockSignals(False)
        self._selected(self.metric_list.currentRow())

    def _selected(self, row):
        if self._editing_metric != row:
            self._sync_editor()
        self.nodes.finish_pick()
        self._editing_metric = int(row)
        visible = 0 <= row < len(self._metrics)
        self.editor.setVisible(visible)
        if not visible:
            self.metric_name.clear()
            self.nodes.clear()
            return
        metric = self._metrics[row]
        self.metric_name.setText(str(metric.get("name", "")))
        self.component.setCurrentIndex(
            max(0, self.component.findData(metric.get("component", "Magnitude")))
        )
        self.nodes.set_definition(_node_definition(metric.get("nodes", ())))

    def _add(self, _checked=False):
        self._sync_editor()
        self._metrics.append({
            "id": uuid4().hex,
            "name": f"Displacement Control-{len(self._metrics) + 1}",
            "kind": "displacement_control",
            "field_name": "DISP",
            "component": "Magnitude",
            "nodes": [],
        })
        self._refresh(len(self._metrics) - 1)

    def _remove(self, _checked=False):
        if self._editing_metric < 0:
            return
        self.nodes.finish_pick()
        del self._metrics[self._editing_metric]
        self._editing_metric = -1
        self._refresh(0)

    def values(self):
        self._sync_editor()
        value = deepcopy(self.original)
        value.name = self.name.text().strip()
        if not value.name:
            raise ValueError("Enter a Study name")
        analysis_id = self.analysis.currentValue()
        analysis = self.project.try_resolve(analysis_id)
        if analysis is None:
            raise ValueError("Select an Analysis")
        value.analysis_ref = EntityRef.of(analysis, "Analysis")
        value.mesh_scales = [
            float(part.strip())
            for part in self.scales.text().replace(";", ",").split(",")
            if part.strip()
        ]
        if (len(value.mesh_scales) < 3
            or any(number <= 0 for number in value.mesh_scales)
            or any(a <= b for a, b in zip(value.mesh_scales, value.mesh_scales[1:]))):
            raise ValueError("Enter at least three strictly decreasing positive mesh sizes")
        value.step_id = int(self.step.text())
        value.relative_tolerance = float(self.tolerance.text()) / 100
        if value.step_id < 1 or not 0 < value.relative_tolerance < 1:
            raise ValueError("Step must be positive; tolerance must be between 0 and 100%")
        names = [spec["name"] for spec in self._metrics]
        if len(names) != len(set(names)) or any(not name for name in names):
            raise ValueError("Displacement control names must be nonempty and unique")
        if not self._metrics:
            raise ValueError("Add at least one Displacement Control")
        for spec in self._metrics:
            if spec.get("component") not in _DISPLACEMENT_COMPONENTS:
                raise ValueError("Only DISP D1–D6 and Magnitude are supported")
        value.metrics = deepcopy(self._metrics)
        value.field_name = "DISP"
        value.component = "Magnitude"
        value.metric = "displacement_max"
        value.exclude_radius = 0.0
        return value

    def _save(self):
        try:
            self._candidate = self.values()
        except (TypeError, ValueError) as exc:
            QMessageBox.warning(self, "Invalid convergence study", str(exc))
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
