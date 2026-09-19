"""Path and Plot dialogs for the shared Results ribbon.

Definitions live in the owning ResultSet's metadata and remain tied to its
original FRD mesh rather than to mutable viewport actor indices.
"""
from __future__ import annotations

from copy import deepcopy
from csv import writer
from pathlib import Path

from PyQt6.QtCore import Qt
from opencae.ui.primitives.inputs import InputFormText
from opencae.ui.primitives.selects import SelectForm
from opencae.ui.primitives.buttons import ButtonFormAction
from opencae.ui.templates import dialog_layout, dialog_buttons, field_block

from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QMessageBox,
    QVBoxLayout, QWidget,
)

from opencae.results.mesh_path import (
    create_mesh_path, finite_series, mesh_graph, path_field_series,
    stored_paths, time_field_series,
)
from opencae.ui.panels.time_manager_plot import TimeManagerPlot


def _error(parent, title, exc):
    QMessageBox.warning(parent, title, str(exc))


class PathEditorDialog(QDialog):
    """Edit one persisted mesh-edge path with the shared Results node picker."""

    def __init__(self, result, store, loader, parent=None, *, path_index=None,
                 viewport=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Path" if path_index is not None else "Add Path")
        self.setMinimumWidth(520)
        self.resize(590, 345)
        self.target_result, self.store, self.loader = result, store, loader
        self.viewport = viewport
        self._path_index = path_index
        self._paths = list(stored_paths(result))
        existing = (self._paths[path_index] if path_index is not None else None)
        self._waypoints = list(existing.waypoints) if existing else []
        self._coordinates = self._adjacency = None
        self._cancel_pick = None
        root = dialog_layout(self)
        self.name = InputFormText(
            existing.name if existing else f"Path-{len(self._paths) + 1}"
        )
        root.addWidget(field_block("Name", self.name))
        self.waypoints = InputFormText(
            ", ".join(map(str, self._waypoints)), read_only=True,
        )
        self.pick = ButtonFormAction("Pick nodes")
        self.pick.setCheckable(True)
        pick_row = QWidget(self)
        pick_layout = QHBoxLayout(pick_row)
        pick_layout.setContentsMargins(0, 0, 0, 0)
        pick_layout.addWidget(self.waypoints, 1)
        pick_layout.addWidget(self.pick)
        root.addWidget(field_block("Waypoint nodes (in order)", pick_row))
        self.default_x = SelectForm()
        self.default_x.addItem("Distance", "distance")
        self.default_x.addItem("Node ID", "node_id")
        if existing:
            self.default_x.setCurrentIndex(
                max(0, self.default_x.findData(existing.default_x_axis))
            )
        root.addWidget(field_block("Path X axis", self.default_x))
        self.description = QLabel(
            "Pick two or more nodes. The route follows the shortest connected "
            "FE-mesh edge path and is highlighted in the Results viewport."
        )
        self.description.setWordWrap(True)
        root.addWidget(self.description)
        root.addStretch(1)
        buttons = dialog_buttons()
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self.pick.toggled.connect(self._toggle_pick)
        self.finished.connect(self._cleanup)
        self._preview()

    def _toggle_pick(self, checked):
        if not checked:
            if self._cancel_pick:
                callback, self._cancel_pick = self._cancel_pick, None
                callback()
            self.pick.setText("Pick nodes")
            return
        if self.viewport is None:
            self.pick.setChecked(False)
            QMessageBox.warning(self, "Pick nodes", "No Results viewport is available")
            return
        self._cancel_pick = self.viewport.begin_result_path_pick(self._picked_node)
        self.pick.setText("Finish picking")

    def _picked_node(self, node_id):
        # The displayed grid's logical node IDs match the source FRD. The
        # ordinary Results query picker already resolves beam surface vertices.
        node_id = int(node_id)
        if not self._waypoints or self._waypoints[-1] != node_id:
            self._waypoints.append(node_id)
            self.waypoints.setText(", ".join(map(str, self._waypoints)))
        self._preview()

    def _preview(self):
        if self.viewport is None:
            return
        if len(self._waypoints) < 2:
            self.viewport.clear_result_path_preview()
            return
        try:
            if self._coordinates is None:
                self._coordinates, self._adjacency = mesh_graph(
                    self.target_result.source_file, self.loader
                )
            candidate = create_mesh_path(
                self.name.text().strip() or "Path",
                self._waypoints, self._coordinates, self._adjacency,
                self.default_x.currentData(),
            )
            self.viewport.show_result_path_preview(
                self._coordinates, candidate.node_ids,
            )
            self.description.setText(
                f"{len(candidate.node_ids)} path nodes; length "
                f"{candidate.distances[-1]:.7g} (undeformed)."
            )
        except (OSError, ValueError, KeyError, RuntimeError) as exc:
            self.viewport.clear_result_path_preview()
            self.description.setText(str(exc))

    def _save(self):
        try:
            if self._coordinates is None:
                self._coordinates, self._adjacency = mesh_graph(
                    self.target_result.source_file, self.loader
                )
            path = create_mesh_path(
                self.name.text(), self._waypoints,
                self._coordinates, self._adjacency,
                self.default_x.currentData(),
            )
            if any(other.name == path.name and i != self._path_index
                   for i, other in enumerate(self._paths)):
                raise ValueError("A path with this name already exists")
            if self._path_index is None:
                self._paths.append(path)
            else:
                self._paths[self._path_index] = path
            metadata = deepcopy(dict(self.target_result.metadata or {}))
            metadata["mesh_paths"] = [item.as_dict() for item in self._paths]
            candidate = deepcopy(self.target_result)
            candidate.metadata = metadata
            if (self.store is not None and self.store.project.try_resolve(
                    self.target_result.id) is not None):
                self.store.replace_entity(
                    f"Saved path {path.name}",
                    self.store.project.id, "results", candidate,
                )
                self.target_result = self.store.project.resolve(candidate.id)
            else:
                self.target_result.metadata = metadata
            self.accept()
        except (OSError, ValueError, TypeError, RuntimeError) as exc:
            _error(self, "Save path", exc)

    def _cleanup(self, *_):
        if self._cancel_pick:
            callback, self._cancel_pick = self._cancel_pick, None
            callback()
        if self.viewport is not None:
            self.viewport.clear_result_path_preview()


class PlotDialog(QDialog):
    """Generate an XY chart from one persisted mesh path or a node's time history."""

    def __init__(self, result, loader, preferred_field=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("XY Plot")
        self.resize(780, 545)
        self.result, self.loader = result, loader
        self._x, self._y = (), ()
        self._x_label = self._y_label = ""
        self._fields = tuple(loader.fields(result.source_file))
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.mode = SelectForm()
        self.mode.addItem("Path", "path")
        self.mode.addItem("Time", "time")
        self.path = SelectForm()
        self.path.addItem("Select path", None)
        for path in stored_paths(result):
            self.path.addItem(path.name, path)
        self.x_axis = SelectForm()
        self.x_axis.addItem("Distance", "distance")
        self.x_axis.addItem("Node ID in path", "node_id")
        self.path.currentIndexChanged.connect(self._path_selected)
        self.node = InputFormText()
        self.node.setPlaceholderText("Node ID for time history")
        self.step = SelectForm()
        for step in sorted({int(f.metadata.get("step_id", 1)) for f in self._fields}):
            self.step.addItem(f"Step {step}", step)
        self.frame = SelectForm()
        self.field = SelectForm()
        self.component = SelectForm()
        form.addRow("X axis", self.mode)
        form.addRow("Path", self.path)
        form.addRow("Path X values", self.x_axis)
        form.addRow("Time history node", self.node)
        form.addRow("Step", self.step)
        form.addRow("Frame (for path)", self.frame)
        form.addRow("Y field", self.field)
        form.addRow("Y component", self.component)
        root.addLayout(form)
        self.chart = TimeManagerPlot()
        self.chart.setMinimumHeight(200)
        root.addWidget(self.chart, 1)
        self.note = QLabel("Select a path and field, then build the plot.")
        self.note.setWordWrap(True)
        root.addWidget(self.note)
        actions = QHBoxLayout()
        build = ButtonFormAction("Build plot")
        export = ButtonFormAction("Export CSV")
        close = ButtonFormAction("Close")
        actions.addWidget(build)
        actions.addWidget(export)
        actions.addStretch(1)
        actions.addWidget(close)
        root.addLayout(actions)
        self.mode.currentIndexChanged.connect(self._mode_changed)
        self.step.currentIndexChanged.connect(self._frames_changed)
        self.field.currentIndexChanged.connect(self._components_changed)
        build.clicked.connect(self._build_series)
        export.clicked.connect(self._export_csv)
        close.clicked.connect(self.accept)
        if preferred_field is not None:
            index = self.step.findData(int(preferred_field.metadata.get("step_id", 1)))
            if index >= 0:
                self.step.setCurrentIndex(index)
        self._frames_changed()
        if preferred_field is not None:
            index = self.field.findData(preferred_field.name)
            if index >= 0:
                self.field.setCurrentIndex(index)
            component = str(preferred_field.metadata.get("component", "Magnitude"))
            index = self.component.findData(component)
            if index >= 0:
                self.component.setCurrentIndex(index)
            frame_id = int(preferred_field.metadata.get("frame_id", 1))
            index = self.frame.findData(frame_id)
            if index >= 0:
                self.frame.setCurrentIndex(index)
        self._mode_changed()

    def _path_selected(self, *_):
        path = self.path.currentData()
        if path is not None:
            index = self.x_axis.findData(path.default_x_axis)
            if index >= 0:
                self.x_axis.setCurrentIndex(index)

    def _mode_changed(self, *_):
        path_mode = self.mode.currentData() == "path"
        self.path.setEnabled(path_mode)
        self.x_axis.setEnabled(path_mode)
        self.frame.setEnabled(path_mode)
        self.node.setEnabled(not path_mode)

    def _frames_changed(self, *_):
        old_frame = self.frame.currentData()
        old_field = self.field.currentData()
        step_id = self.step.currentData()
        sources = [f for f in self._fields
                   if int(f.metadata.get("step_id", 1)) == step_id]
        self.frame.blockSignals(True)
        self.frame.clear()
        frames = sorted({int(f.metadata.get("frame_id", 1)): float(
            f.metadata.get("frame_value", 0.0)) for f in sources}.items())
        for frame_id, value in frames:
            self.frame.addItem(f"Frame {frame_id} ({value:.6g})", frame_id)
        if old_frame is not None and self.frame.findData(old_frame) >= 0:
            self.frame.setCurrentIndex(self.frame.findData(old_frame))
        self.frame.blockSignals(False)
        self.field.blockSignals(True)
        self.field.clear()
        for name in dict.fromkeys(f.name for f in sources):
            self.field.addItem(name, name)
        if old_field is not None and self.field.findData(old_field) >= 0:
            self.field.setCurrentIndex(self.field.findData(old_field))
        self.field.blockSignals(False)
        self._components_changed()

    def _components_changed(self, *_):
        name, step = self.field.currentData(), self.step.currentData()
        preferred = self.component.currentData()
        self.component.clear()
        source = next((f for f in self._fields
                       if f.name == name and int(f.metadata.get("step_id", 1)) == step), None)
        if source is None:
            return
        for component in dict.fromkeys((
            "Magnitude", *source.metadata.get("components", ()),
            *source.metadata.get("derived", ()),
        )):
            self.component.addItem(component, component)
        if preferred is not None and self.component.findData(preferred) >= 0:
            self.component.setCurrentIndex(self.component.findData(preferred))

    def _build_series(self):
        try:
            source = self.result.source_file
            name = self.field.currentData()
            component = self.component.currentData()
            step = self.step.currentData()
            if name is None or component is None or step is None:
                raise ValueError("Select a field, component and Step")
            if self.mode.currentData() == "path":
                path = self.path.currentData()
                if path is None:
                    raise ValueError("Create or select a mesh Path first")
                axis = self.x_axis.currentData()
                x, y = path_field_series(
                    self.loader, source, path, name, component, step,
                    self.frame.currentData(), axis,
                )
                self._x_label = "Distance" if axis == "distance" else "Node ID"
                self.note.setText(
                    f"{path.name}: {len(x)} nodes, {len(x) - len(finite_series(x,y)[0])} "
                    "missing samples. Distance uses undeformed FE coordinates."
                )
            else:
                node = int(self.node.text().strip())
                if node not in self.loader.read(source).nodes:
                    raise ValueError(f"Node {node} is absent from this result mesh")
                x, y = time_field_series(
                    self.loader, source, node, name, component, step
                )
                self._x_label = "Time / solver frame value"
                self.note.setText(
                    f"Node {node}: {len(x)} frames. X uses solver-provided "
                    "frame values; values are not synthesized between frames."
                )
            self._x, self._y = finite_series(x, y)
            if not self._x:
                raise ValueError("No finite field samples are available")
            self._y_label = f"{name}: {component}"
            self.chart.set_series(
                self._x, self._y, x_label=self._x_label,
                y_label=self._y_label, interactive=False,
                range_editable=False, show_play_range=False,
            )
        except (OSError, ValueError, TypeError, RuntimeError, KeyError) as exc:
            self._x, self._y = (), ()
            _error(self, "XY plot", exc)

    def _export_csv(self):
        if not self._x:
            _error(self, "Export CSV", "Build a plot before exporting")
            return
        name, _ = QFileDialog.getSaveFileName(
            self, "Export XY plot", "plot.csv", "CSV files (*.csv)"
        )
        if not name:
            return
        target = Path(name).with_suffix(".csv")
        try:
            with target.open("w", newline="", encoding="utf-8") as handle:
                output = writer(handle)
                output.writerow((self._x_label, self._y_label))
                output.writerows(zip(self._x, self._y))
        except OSError as exc:
            _error(self, "Export CSV", exc)
