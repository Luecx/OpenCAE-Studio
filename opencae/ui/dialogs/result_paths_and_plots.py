"""Path and Plot dialogs for the shared Results ribbon.

Definitions live in the owning ResultSet's metadata and remain tied to its
original FRD mesh rather than to mutable viewport actor indices.
"""
from __future__ import annotations

from copy import deepcopy
from csv import writer
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
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
    def __init__(self, result, store, loader, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mesh Paths")
        self.resize(540, 300)
        self.target_result, self.store, self.loader = result, store, loader
        self._paths = list(stored_paths(result))
        self._coordinates = self._adjacency = None
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.existing = QComboBox()
        self.name = QLineEdit()
        self.waypoints = QLineEdit()
        self.waypoints.setPlaceholderText("e.g. 12, 28, 40")
        self.waypoints.setToolTip(
            "Enter two or more waypoint node IDs; each pair follows mesh edges."
        )
        form.addRow("Saved path", self.existing)
        form.addRow("Name", self.name)
        form.addRow("Waypoint node IDs", self.waypoints)
        root.addLayout(form)
        self.description = QLabel()
        self.description.setWordWrap(True)
        root.addWidget(self.description)
        controls = QHBoxLayout()
        new = QPushButton("New")
        save = QPushButton("Save path")
        delete = QPushButton("Delete path")
        controls.addWidget(new)
        controls.addWidget(save)
        controls.addWidget(delete)
        root.addLayout(controls)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        root.addWidget(close)
        self.existing.currentIndexChanged.connect(self._selected)
        new.clicked.connect(self._new)
        save.clicked.connect(self._save)
        delete.clicked.connect(self._delete)
        self._refresh()

    def _refresh(self, selected=None):
        self.existing.blockSignals(True)
        self.existing.clear()
        self.existing.addItem("New path", -1)
        for index, path in enumerate(self._paths):
            self.existing.addItem(path.name, index)
        if selected is not None:
            self.existing.setCurrentIndex(int(selected) + 1)
        self.existing.blockSignals(False)
        self._selected()

    def _selected(self, *_):
        index = self.existing.currentData()
        if index is None or index < 0:
            self.name.clear()
            self.waypoints.clear()
            self.description.setText(
                "Choose waypoint nodes on the original FE mesh. The shortest "
                "connected mesh-edge route joins consecutive waypoints."
            )
            return
        path = self._paths[index]
        self.name.setText(path.name)
        self.waypoints.setText(", ".join(map(str, path.waypoints)))
        self.description.setText(
            f"{len(path.node_ids)} path nodes; total undeformed length "
            f"{path.distances[-1]:.7g}. The path follows actual FE edges."
        )

    def _new(self):
        self.existing.setCurrentIndex(0)

    def _persist(self):
        metadata = deepcopy(dict(self.target_result.metadata or {}))
        metadata["mesh_paths"] = [item.as_dict() for item in self._paths]
        candidate = deepcopy(self.target_result)
        candidate.metadata = metadata
        if (self.store is not None
                and self.store.project.try_resolve(self.target_result.id) is not None):
            self.store.replace_entity(
                f"Updated paths for {self.target_result.name}",
                self.store.project.id, "results", candidate,
            )
            self.target_result = self.store.project.resolve(candidate.id)
        else:
            # External FRD files not attached to a Project have session paths.
            self.target_result.metadata = metadata

    def _save(self):
        try:
            anchors = tuple(int(token.strip()) for token in
                            self.waypoints.text().replace(";", ",").split(",")
                            if token.strip())
            if self._coordinates is None:
                self._coordinates, self._adjacency = mesh_graph(
                    self.target_result.source_file, self.loader
                )
            path = create_mesh_path(
                self.name.text(), anchors, self._coordinates, self._adjacency
            )
            index = self.existing.currentData()
            if index is None or index < 0:
                if any(item.name == path.name for item in self._paths):
                    raise ValueError("A path with this name already exists")
                self._paths.append(path)
                index = len(self._paths) - 1
            else:
                if any(item.name == path.name and i != index
                       for i, item in enumerate(self._paths)):
                    raise ValueError("A path with this name already exists")
                self._paths[index] = path
            self._persist()
            self._refresh(index)
        except (OSError, ValueError, TypeError, RuntimeError) as exc:
            _error(self, "Save path", exc)

    def _delete(self):
        index = self.existing.currentData()
        if index is None or index < 0:
            return
        try:
            del self._paths[index]
            self._persist()
            self._refresh()
        except (OSError, ValueError, TypeError, RuntimeError) as exc:
            _error(self, "Delete path", exc)


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
        self.mode = QComboBox()
        self.mode.addItem("Path", "path")
        self.mode.addItem("Time", "time")
        self.path = QComboBox()
        self.path.addItem("Select path", None)
        for path in stored_paths(result):
            self.path.addItem(path.name, path)
        self.x_axis = QComboBox()
        self.x_axis.addItem("Distance", "distance")
        self.x_axis.addItem("Node ID in path", "node_id")
        self.node = QLineEdit()
        self.node.setPlaceholderText("Node ID for time history")
        self.step = QComboBox()
        for step in sorted({int(f.metadata.get("step_id", 1)) for f in self._fields}):
            self.step.addItem(f"Step {step}", step)
        self.frame = QComboBox()
        self.field = QComboBox()
        self.component = QComboBox()
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
        build = QPushButton("Build plot")
        export = QPushButton("Export CSV")
        close = QPushButton("Close")
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
