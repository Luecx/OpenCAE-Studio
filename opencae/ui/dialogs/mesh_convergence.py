"""Canonical OpenCAE form for displacement-only mesh-convergence studies."""
from __future__ import annotations

from copy import deepcopy
from csv import writer
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QMessageBox, QVBoxLayout, QWidget, QLabel,
)

from opencae.controllers.region_selection import begin_region_pick
from opencae.model.core import EntityRef
from opencae.model.entities.studies import MeshConvergenceStudy
from opencae.model.selection import (
    MeshNodeOperand, RegionDefinition, RegionSelectionItem,
    RegionProjection, RegionRequirement,
    SelectableKind, SelectionOperation, SelectionPolicy,
)
from opencae.results.mesh_convergence import assess_convergence, assess_all_metrics
from opencae.ui.core.widgets import CompactRegionSelector, ReferenceSelector
from opencae.ui.panels.time_manager_plot import TimeManagerPlot
from opencae.ui.primitives.buttons import ButtonFormAction
from opencae.ui.primitives.inputs import InputFormText, InputFormInteger, InputFormNumber
from opencae.ui.primitives.selects import SelectForm
from opencae.ui.templates import (
    SectionHeading, dialog_buttons, dialog_layout, field_block, field_row,
)


_DISPLACEMENT_COMPONENTS = ("Magnitude", "D1", "D2", "D3", "D4", "D5", "D6")


def _nodes_from_definition(definition):
    values = {}
    for item in definition.items:
        operand = item.operand
        if not isinstance(operand, MeshNodeOperand):
            raise ValueError("Only individual mesh nodes are valid in a Displacement Control")
        if item.picked_position is None:
            raise ValueError("Selected node has no original spatial position")
        entry = {
            "node_id": operand.node_id,
            "owner_id": operand.owner_ref.entity_id,
            "instance_id": operand.instance_ref.entity_id if operand.instance_ref else "",
            "position": list(item.picked_position),
            "label": item.display_label or f"Node-{operand.node_id}",
        }
        # RegionSelectionItems from reopened Studies can carry a different
        # mesh_revision than newly picked hits. Their stable physical identity
        # here is (owner, instance, original node ID), not that revision.
        key = (entry["owner_id"], entry["instance_id"], entry["node_id"])
        values[key] = entry
    return list(values.values())


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
    """One Study metric, standard OpenCAE fields and persistent node highlights."""

    _PREVIEW = "mesh-convergence-monitor-nodes"

    def __init__(self, project, study=None, parent=None):
        super().__init__(parent)
        self.project = project
        self.viewport = getattr(parent, "viewport", None)
        self.original = deepcopy(study) if isinstance(study, MeshConvergenceStudy) else MeshConvergenceStudy(
            name=f"Mesh Convergence-{len(project.studies) + 1}"
        )
        self._candidate = None
        self.setWindowTitle("Mesh Convergence Study")
        self.setMinimumWidth(590)
        self.resize(660, 540)
        root = dialog_layout(self)
        self.name = InputFormText(self.original.name)
        root.addWidget(field_block("Name", self.name))
        self.analysis = ReferenceSelector(
            [(item.name, item.id) for item in project.analyses],
            self.original.analysis_ref.entity_id,
        )
        root.addWidget(field_block("Analysis", self.analysis))
        self.factor = InputFormNumber(
            self.original.mesh_scaling_factor, minimum=0.01, maximum=0.99,
            decimals=4,
        )
        self.iterations = InputFormInteger(
            self.original.max_iterations, minimum=3, maximum=100,
        )
        root.addWidget(field_row(
            field_block("Mesh scaling factor", self.factor),
            field_block("Maximum iterations", self.iterations),
        ))
        self.step = InputFormInteger(self.original.step_id, minimum=1, maximum=100000)
        self.tolerance = InputFormNumber(
            100 * self.original.relative_tolerance,
            minimum=0.000001, maximum=99.9999, decimals=5,
        )
        root.addWidget(field_row(
            field_block("Analysis Step ID", self.step),
            field_block("Tolerance (%)", self.tolerance),
        ))
        root.addWidget(SectionHeading("Convergence Metric"))
        self.metric = SelectForm()
        self.metric.addItem("Displacement", "displacement_control")
        root.addWidget(field_block("Type", self.metric))
        self.component = SelectForm()
        for name in _DISPLACEMENT_COMPONENTS:
            self.component.addItem(name, name)
        previous = next(
            (m for m in self.original.metrics
             if m.get("kind") == "displacement_control"), {},
        )
        self.component.setCurrentIndex(max(
            0, self.component.findData(previous.get("component", "Magnitude"))
        ))
        root.addWidget(field_block("Component", self.component))
        nodes = deepcopy(previous.get("nodes", ()))
        for node in nodes:
            if not node.get("owner_id"):
                instance = project.try_resolve(node.get("instance_id", ""))
                part = (project.try_resolve(instance.part_ref) if instance is not None
                        else project.parts[0] if len(project.parts) == 1 else None)
                if part is not None:
                    node["owner_id"] = part.id
        self.nodes = CompactRegionSelector(
            project, definition=_node_definition(nodes),
            pick_callback=self._pick_nodes,
            options=(), show_extended=True,
            extended_title="Choose monitoring nodes",
            requirement=RegionRequirement(
                RegionProjection.NODES, allowed_dimensions=(0,), min_count=0,
            ),
            allow_part_local=True, parent=self,
        )
        root.addWidget(field_block("Monitor nodes (optional)", self.nodes))
        hint = QLabel(
            "No nodes selected: monitor the global displacement maximum. "
            "Each iteration multiplies the preceding element size by the scaling "
            "factor. Stop when all monitored values converge or the maximum "
            "number of iterations is reached."
        )
        hint.setWordWrap(True)
        root.addWidget(hint)
        root.addStretch(1)
        buttons = dialog_buttons()
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self.nodes.value_changed.connect(self._highlight_nodes)
        self.finished.connect(self._finished)
        self._highlight_nodes()

    def _highlight_nodes(self, *_):
        if self.viewport is not None:
            self.viewport.show_region_preview(
                self._PREVIEW, self.nodes.definition(),
                point_size=18, show_point_labels=True,
            )

    def _finished(self, *_):
        self.nodes.finish_pick()
        if self.viewport is not None:
            self.viewport.clear_region_preview(self._PREVIEW)

    def _pick_nodes(self, _widget, done, finished):
        if self.viewport is None:
            QMessageBox.warning(self, "Select nodes", "No active viewport is available")
            return None
        if not any(part.mesh.node_count for part in self.project.parts):
            QMessageBox.warning(self, "Select nodes", "Generate a mesh before choosing nodes")
            return None
        self.viewport.set_display_mode("mesh")
        policy = SelectionPolicy.create({SelectableKind.MESH_NODE}, multiple=True)
        default_owner = self.project.parts[0] if len(self.project.parts) == 1 else None

        def selected(definition, operation):
            done(
                definition,
                SelectionOperation.REMOVE if operation == SelectionOperation.REMOVE
                else SelectionOperation.ADD,
            )

        return begin_region_pick(
            self.project, self.viewport, policy, selected,
            default_owner=default_owner, finished=finished,
        )

    def values(self):
        value = deepcopy(self.original)
        value.name = self.name.text().strip()
        if not value.name:
            raise ValueError("Enter a Study name")
        analysis = self.project.try_resolve(self.analysis.currentValue())
        if analysis is None:
            raise ValueError("Select an Analysis")
        value.analysis_ref = EntityRef.of(analysis, "Analysis")
        value.mesh_scaling_factor = float(self.factor.value())
        value.max_iterations = int(self.iterations.value())
        value.mesh_scales = [
            value.mesh_scaling_factor ** index
            for index in range(value.max_iterations)
        ]
        value.step_id = self.step.value()
        value.relative_tolerance = self.tolerance.value() / 100.
        nodes = _nodes_from_definition(self.nodes.definition())
        value.metrics = [{
            "id": "displacement",
            "kind": "displacement_control",
            "name": "Displacement",
            "field_name": "DISP",
            "component": self.component.currentData(),
            "nodes": nodes,
        }]
        value.field_name = "DISP"
        value.component = self.component.currentData()
        value.metric = "displacement_max" if not nodes else "probe"
        value.exclude_radius = 0.
        return value

    def _save(self):
        try:
            self._candidate = self.values()
        except (TypeError, ValueError) as exc:
            QMessageBox.warning(self, "Invalid convergence Study", str(exc))
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
            f"Completed mesh levels: {len(samples)}. "
            "No automatic singularity detection or exclusion is applied. "
            "This is a displacement trend, not a certified numerical error estimate. "
            "Individual levels are available as ordinary Results in the browser."
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
