"""OpenCAE-styled parametric sketch and feature editor."""

from __future__ import annotations

from copy import deepcopy
from math import hypot

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from opencae.model.entities.geometry import (
    SketchArc,
    SketchAxis,
    SketchCircle,
    SketchConstraintKind,
    SketchFeature,
    SketchFeatureMode,
    SketchLine,
    SketchPoint,
)
from opencae.sketch import constraint_label, solve_sketch
from opencae.ui.core.icon_factory import IconKind, make_icon

from .canvas import SketchCanvas
from .preview import SketchFeaturePreview


class SketchFeatureDialog(QDialog):
    """Large modal feature editor with a ribbon-like toolbar and 2D/3D workspace."""

    def __init__(
        self,
        feature: SketchFeature | None = None,
        *,
        mode: SketchFeatureMode | str = SketchFeatureMode.EXTRUSION,
        feature_name: str = "Sketch-1",
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("SketchFeatureDialog")
        self.setWindowTitle(
            "Edit Sketch Feature" if feature else "Create Sketch Feature"
        )
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
        self.resize(1280, 820)
        self.setMinimumSize(920, 620)

        self._feature = (
            deepcopy(feature)
            if feature is not None
            else SketchFeature(name=feature_name, mode=mode)
        )
        self._updating_controls = False
        self._tool_actions: dict[str, QAction] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_toolbar())

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setObjectName("SketchWorkspaceSplitter")
        self.workspace = QStackedWidget(splitter)
        self.canvas = SketchCanvas(self._feature.sketch, self.workspace)
        self.preview = SketchFeaturePreview(self.workspace)
        self.workspace.addWidget(self.canvas)
        self.workspace.addWidget(self.preview)
        splitter.addWidget(self.workspace)
        splitter.addWidget(self._build_inspector(splitter))
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([1000, 280])
        root.addWidget(splitter, 1)
        root.addWidget(self._build_footer())

        self._wire()
        self._sync_feature_controls()
        self._sync_constraints()
        self._update_solver_status(solve_sketch(self.canvas.sketch))
        self.canvas.set_revolve_axis_visible(
            self._feature.mode is SketchFeatureMode.REVOLVE
        )

    @property
    def feature(self) -> SketchFeature:
        self._collect_feature()
        return deepcopy(self._feature)

    def values(self):
        """Compatibility with generic dialog runners."""
        return {"feature": self.feature}

    # --------------------------------------------------------------- building
    def _build_toolbar(self):
        host = QWidget(self)
        host.setObjectName("SketchRibbonHost")
        layout = QVBoxLayout(host)
        layout.setContentsMargins(8, 6, 8, 5)
        layout.setSpacing(4)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(6)
        self.toolbar = QToolBar(host)
        self.toolbar.setObjectName("SketchToolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextUnderIcon
        )
        top.addWidget(self.toolbar, 1)

        self.view_sketch = QToolButton(host)
        self.view_sketch.setText("Sketch")
        self.view_sketch.setCheckable(True)
        self.view_sketch.setChecked(True)
        self.view_sketch.setAutoRaise(True)
        self.view_preview = QToolButton(host)
        self.view_preview.setText("3D Preview")
        self.view_preview.setCheckable(True)
        self.view_preview.setAutoRaise(True)
        view_group = QButtonGroup(host)
        view_group.setExclusive(True)
        view_group.addButton(self.view_sketch)
        view_group.addButton(self.view_preview)
        top.addWidget(self.view_sketch)
        top.addWidget(self.view_preview)
        layout.addLayout(top)

        self._add_tool_action("Select", "Select", IconKind.PART)
        self.toolbar.addSeparator()
        undo = self.toolbar.addAction(make_icon(IconKind.UNDO, 18), "Undo")
        redo = self.toolbar.addAction(make_icon(IconKind.REDO, 18), "Redo")
        # The toolbar is built before the canvas. Resolve the canvas lazily when
        # the action is triggered instead of dereferencing it during construction.
        undo.triggered.connect(
            lambda _checked=False: self.canvas.undo()
        )
        redo.triggered.connect(
            lambda _checked=False: self.canvas.redo()
        )
        self.toolbar.addSeparator()
        for tool, label in (
            ("Point", "Point"),
            ("Line", "Line"),
            ("Polyline", "Polyline"),
            ("Rectangle", "Rectangle"),
            ("Circle", "Circle"),
            ("Center Arc", "Arc"),
            ("3-Point Arc", "3P Arc"),
            ("Ellipse", "Ellipse"),
            ("Spline", "Spline"),
            ("Slot", "Slot"),
        ):
            self._add_tool_action(tool, label, IconKind.PART)

        self.toolbar.addSeparator()
        self.construction_action = self.toolbar.addAction("Construction")
        self.construction_action.setCheckable(True)
        self.grid_action = self.toolbar.addAction("Grid")
        self.grid_action.setCheckable(True)
        self.grid_action.setChecked(True)
        self.snap_action = self.toolbar.addAction("Snap")
        self.snap_action.setCheckable(True)
        self.snap_action.setChecked(True)
        self.fit_action = self.toolbar.addAction(
            make_icon(IconKind.FIT_VIEW, 18), "Fit"
        )
        self.toolbar.addSeparator()

        for label, kind in (
            ("Coincident", "Coincident"),
            ("Horizontal", "Horizontal"),
            ("Vertical", "Vertical"),
            ("Parallel", "Parallel"),
            ("Perp.", "Perpendicular"),
            ("Tangent", "Tangent"),
            ("Equal", "Equal"),
            ("Concentric", "Concentric"),
            ("Midpoint", "Midpoint"),
            ("Fixed", "Fixed"),
        ):
            action = self.toolbar.addAction(label)
            action.setProperty("constraintKind", kind)
            action.triggered.connect(
                lambda _checked=False, value=kind: self._apply_constraint(value)
            )

        self.toolbar.addSeparator()
        for label, kind in (
            ("Distance", "Distance"),
            ("Horizontal dim", "DistanceX"),
            ("Vertical dim", "DistanceY"),
            ("Angle", "Angle"),
            ("Radius", "Radius"),
            ("Diameter", "Diameter"),
        ):
            action = self.toolbar.addAction(label)
            action.setProperty("dimensionKind", kind)
            action.triggered.connect(
                lambda _checked=False, value=kind: self._apply_dimension(value)
            )

        self._tool_group = QActionGroup(host)
        self._tool_group.setExclusive(True)
        for action in self._tool_actions.values():
            self._tool_group.addAction(action)
        self._tool_actions["Select"].setChecked(True)
        return host

    def _add_tool_action(self, tool: str, label: str, icon_kind):
        action = QAction(make_icon(icon_kind, 18), label, self)
        action.setCheckable(True)
        action.setData(tool)
        action.triggered.connect(
            lambda checked=False, value=tool: (
                self.canvas.set_tool(value) if checked else None
            )
        )
        self.toolbar.addAction(action)
        self._tool_actions[tool] = action

    def _build_inspector(self, parent):
        panel = QFrame(parent)
        panel.setObjectName("SketchInspector")
        panel.setMinimumWidth(250)
        panel.setMaximumWidth(360)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("FEATURE", panel)
        title.setObjectName("SketchInspectorHeading")
        layout.addWidget(title)
        layout.addWidget(QLabel("Name", panel))
        self.name_edit = QLineEdit(panel)
        layout.addWidget(self.name_edit)
        layout.addWidget(QLabel("Type", panel))
        self.mode_combo = QComboBox(panel)
        self.mode_combo.addItems(tuple(mode.value for mode in SketchFeatureMode))
        layout.addWidget(self.mode_combo)
        layout.addWidget(QLabel("Operation", panel))
        self.operation_combo = QComboBox(panel)
        self.operation_combo.addItems(("New", "Add", "Cut", "Intersect"))
        layout.addWidget(self.operation_combo)

        self.depth_label = QLabel("Depth", panel)
        self.depth_spin = self._length_spin(panel)
        self.angle_label = QLabel("Angle", panel)
        self.angle_spin = QDoubleSpinBox(panel)
        self.angle_spin.setRange(0.001, 360.0)
        self.angle_spin.setDecimals(3)
        self.angle_spin.setSingleStep(5.0)
        self.angle_spin.setSuffix("°")
        layout.addWidget(self.depth_label)
        layout.addWidget(self.depth_spin)
        layout.addWidget(self.angle_label)
        layout.addWidget(self.angle_spin)

        self.symmetric_check = QCheckBox("Symmetric about sketch plane", panel)
        self.reverse_check = QCheckBox("Reverse direction", panel)
        layout.addWidget(self.symmetric_check)
        layout.addWidget(self.reverse_check)
        self.axis_note = QLabel(
            "Revolve axis: X axis\nShown dash-dot in the sketch.", panel
        )
        self.axis_note.setWordWrap(True)
        self.axis_note.setObjectName("SketchAxisNote")
        layout.addWidget(self.axis_note)

        separator = QFrame(panel)
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)
        constraints_title = QLabel("CONSTRAINTS & DIMENSIONS", panel)
        constraints_title.setObjectName("SketchInspectorHeading")
        layout.addWidget(constraints_title)
        self.constraint_list = QListWidget(panel)
        self.constraint_list.setObjectName("SketchConstraintList")
        layout.addWidget(self.constraint_list, 1)
        constraint_row = QHBoxLayout()
        self.delete_constraint_button = QPushButton("Remove", panel)
        self.solve_button = QPushButton("Solve", panel)
        constraint_row.addWidget(self.delete_constraint_button)
        constraint_row.addWidget(self.solve_button)
        layout.addLayout(constraint_row)

        separator2 = QFrame(panel)
        separator2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator2)
        options_title = QLabel("SKETCH OPTIONS", panel)
        options_title.setObjectName("SketchInspectorHeading")
        layout.addWidget(options_title)
        self.auto_constraints_check = QCheckBox(
            "Automatic H/V constraints", panel
        )
        self.auto_constraints_check.setChecked(True)
        self.snap_grid_check = QCheckBox("Snap to grid", panel)
        self.snap_grid_check.setChecked(self.canvas.sketch.snap_grid)
        self.snap_geometry_check = QCheckBox("Snap to geometry", panel)
        self.snap_geometry_check.setChecked(self.canvas.sketch.snap_geometry)
        self.show_dimensions_check = QCheckBox("Show dimensions", panel)
        self.show_dimensions_check.setChecked(True)
        layout.addWidget(self.auto_constraints_check)
        layout.addWidget(self.snap_grid_check)
        layout.addWidget(self.snap_geometry_check)
        layout.addWidget(self.show_dimensions_check)
        return panel

    def _build_footer(self):
        footer = QWidget(self)
        footer.setObjectName("SketchFooter")
        row = QHBoxLayout(footer)
        row.setContentsMargins(10, 6, 10, 7)
        row.setSpacing(8)
        self.status_label = QLabel("Ready", footer)
        self.status_label.setObjectName("SketchStatus")
        self.hint_label = QLabel("", footer)
        self.hint_label.setObjectName("SketchHint")
        row.addWidget(self.status_label)
        row.addWidget(self.hint_label, 1)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok,
            parent=footer,
        )
        ok = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok.setText(
            "Create Feature"
            if self.windowTitle().startswith("Create")
            else "Apply"
        )
        row.addWidget(self.buttons)
        return footer

    # ---------------------------------------------------------------- wiring
    def _wire(self):
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.view_sketch.clicked.connect(
            lambda: self.workspace.setCurrentWidget(self.canvas)
        )
        self.view_preview.clicked.connect(self._show_preview)
        self.construction_action.toggled.connect(self.canvas.set_construction)
        self.grid_action.toggled.connect(self.canvas.set_grid_visible)
        self.snap_action.toggled.connect(self._set_snap_enabled)
        self.fit_action.triggered.connect(self.canvas.fit_sketch)
        self.canvas.sketch_changed.connect(self._on_sketch_changed)
        self.canvas.solver_changed.connect(self._update_solver_status)
        self.canvas.status_message.connect(self.hint_label.setText)
        self.mode_combo.currentTextChanged.connect(self._feature_mode_changed)
        self.operation_combo.currentTextChanged.connect(self._feature_value_changed)
        self.depth_spin.valueChanged.connect(self._feature_value_changed)
        self.angle_spin.valueChanged.connect(self._feature_value_changed)
        self.symmetric_check.toggled.connect(self._feature_value_changed)
        self.reverse_check.toggled.connect(self._feature_value_changed)
        self.name_edit.textChanged.connect(self._feature_value_changed)
        self.delete_constraint_button.clicked.connect(self._delete_constraint)
        self.solve_button.clicked.connect(self._solve_now)
        self.auto_constraints_check.toggled.connect(
            lambda value: setattr(self.canvas, "auto_constraints", bool(value))
        )
        self.snap_grid_check.toggled.connect(self._snap_options_changed)
        self.snap_geometry_check.toggled.connect(self._snap_options_changed)
        self.show_dimensions_check.toggled.connect(
            self.canvas.set_dimensions_visible
        )

    # ------------------------------------------------------------- constraints
    def _apply_constraint(self, kind: SketchConstraintKind | str):
        kind = SketchConstraintKind.coerce(kind)
        points = self.canvas.selected_points()
        entities = self.canvas.selected_entities()

        if kind is SketchConstraintKind.COINCIDENT:
            refs = points[:2]
            if len(refs) != 2:
                return self._selection_warning("Select exactly two sketch points")
        elif kind in {
            SketchConstraintKind.PARALLEL,
            SketchConstraintKind.PERPENDICULAR,
            SketchConstraintKind.TANGENT,
            SketchConstraintKind.EQUAL,
            SketchConstraintKind.CONCENTRIC,
        }:
            refs = entities[:2]
            if len(refs) != 2:
                return self._selection_warning(
                    "Select exactly two compatible sketch entities"
                )
        elif kind is SketchConstraintKind.MIDPOINT:
            if len(points) < 1 or len(entities) < 1:
                return self._selection_warning("Select one point and one line")
            refs = (points[0], entities[0])
        elif kind in {
            SketchConstraintKind.HORIZONTAL,
            SketchConstraintKind.VERTICAL,
        }:
            refs = entities[:1] if entities else points[:2]
            if len(refs) not in {1, 2}:
                return self._selection_warning("Select one line or two points")
        elif kind is SketchConstraintKind.FIXED:
            refs = points + entities
            if not refs:
                return self._selection_warning("Select geometry to fix")
        else:
            refs = self.canvas.selected_refs()

        if self.canvas.add_constraint(kind, refs):
            self._sync_constraints()

    def _apply_dimension(self, kind: SketchConstraintKind | str):
        kind = SketchConstraintKind.coerce(kind)
        points = self.canvas.selected_points()
        entities = self.canvas.selected_entities()

        if kind is SketchConstraintKind.DISTANCE:
            if len(points) >= 2:
                refs = points[:2]
                default = self._point_distance(points[0], points[1])
            elif len(entities) == 1 and isinstance(entities[0], SketchLine):
                refs = entities
                default = self._line_length(entities[0])
            else:
                return self._selection_warning("Select two points or one line")
            value = self._ask_value("Distance", default)
        elif kind in {
            SketchConstraintKind.DISTANCE_X,
            SketchConstraintKind.DISTANCE_Y,
        }:
            if len(points) < 2:
                return self._selection_warning("Select exactly two points")
            refs = points[:2]
            first, second = points[:2]
            if kind is SketchConstraintKind.DISTANCE_X:
                default = second.x - first.x
                title = "Horizontal distance"
            else:
                default = second.y - first.y
                title = "Vertical distance"
            value = self._ask_value(
                title, default, allow_negative=True
            )
        elif kind is SketchConstraintKind.ANGLE:
            if len(entities) < 2 or not all(
                isinstance(entity, SketchLine) for entity in entities[:2]
            ):
                return self._selection_warning("Select two lines")
            refs = entities[:2]
            value = self._ask_value("Angle", 90.0, maximum=360.0)
        elif kind in {
            SketchConstraintKind.RADIUS,
            SketchConstraintKind.DIAMETER,
        }:
            if len(entities) != 1 or not isinstance(
                entities[0], (SketchCircle, SketchArc)
            ):
                return self._selection_warning(
                    "Select one circle or circular arc"
                )
            refs = entities
            radius = self._radius(entities[0])
            default = (
                radius
                if kind is SketchConstraintKind.RADIUS
                else 2.0 * radius
            )
            value = self._ask_value(kind.value, default)
        else:
            return

        if value is None:
            return
        if self.canvas.add_constraint(kind, tuple(refs), value):
            self._sync_constraints()

    def _delete_constraint(self):
        item = self.constraint_list.currentItem()
        if item is None:
            return
        constraint_id = item.data(Qt.ItemDataRole.UserRole)
        before = len(self.canvas.sketch.constraints)
        self.canvas._push_history()
        self.canvas.sketch.constraints = [
            constraint
            for constraint in self.canvas.sketch.constraints
            if constraint.id != constraint_id
        ]
        if len(self.canvas.sketch.constraints) != before:
            self.canvas._changed()
        self._sync_constraints()

    def _sync_constraints(self):
        current_id = None
        current = (
            self.constraint_list.currentItem()
            if hasattr(self, "constraint_list")
            else None
        )
        if current is not None:
            current_id = current.data(Qt.ItemDataRole.UserRole)
        self.constraint_list.clear()
        for constraint in self.canvas.sketch.constraints:
            item = QListWidgetItem(constraint_label(constraint))
            item.setData(Qt.ItemDataRole.UserRole, constraint.id)
            if not constraint.driving:
                item.setToolTip("Reference / driven dimension")
            else:
                item.setToolTip(
                    ", ".join(self._reference_label(ref) for ref in constraint.refs)
                )
            self.constraint_list.addItem(item)
            if constraint.id == current_id:
                self.constraint_list.setCurrentItem(item)

    @staticmethod
    def _reference_label(ref) -> str:
        if isinstance(ref, SketchPoint):
            return f"Point {ref.id}"
        return f"{type(ref).__name__.removeprefix('Sketch')} {ref.id}"

    # --------------------------------------------------------------- feature
    def _sync_feature_controls(self):
        self._updating_controls = True
        try:
            self.name_edit.setText(self._feature.name)
            self.mode_combo.setCurrentText(self._feature.mode.value)
            self.operation_combo.setCurrentText(self._feature.operation.value)
            self.depth_spin.setValue(float(self._feature.depth))
            self.angle_spin.setValue(float(self._feature.angle_degrees))
            self.symmetric_check.setChecked(bool(self._feature.symmetric))
            self.reverse_check.setChecked(bool(self._feature.reverse))
            self._refresh_feature_visibility()
        finally:
            self._updating_controls = False

    def _collect_feature(self):
        self._feature.name = self.name_edit.text().strip() or "Sketch Feature"
        self._feature.mode = self.mode_combo.currentText()
        self._feature.operation = self.operation_combo.currentText()
        self._feature.depth = max(float(self.depth_spin.value()), 1.0e-9)
        self._feature.angle_degrees = max(
            float(self.angle_spin.value()), 1.0e-6
        )
        self._feature.symmetric = bool(self.symmetric_check.isChecked())
        self._feature.reverse = bool(self.reverse_check.isChecked())
        self._feature.revolve_axis = SketchAxis.X
        self._feature.sketch = self.canvas.snapshot()

    def _feature_mode_changed(self, value):
        self._refresh_feature_visibility()
        self.canvas.set_revolve_axis_visible(
            SketchFeatureMode.coerce(value) is SketchFeatureMode.REVOLVE
        )
        self._feature_value_changed()

    def _feature_value_changed(self, *_args):
        if self._updating_controls:
            return
        self._collect_feature()

    def _refresh_feature_visibility(self):
        mode = SketchFeatureMode.coerce(self.mode_combo.currentText())
        extrusion = mode is SketchFeatureMode.EXTRUSION
        revolve = mode is SketchFeatureMode.REVOLVE
        self.depth_label.setVisible(extrusion)
        self.depth_spin.setVisible(extrusion)
        self.angle_label.setVisible(revolve)
        self.angle_spin.setVisible(revolve)
        self.axis_note.setVisible(revolve)
        self.symmetric_check.setVisible(extrusion or revolve)
        self.reverse_check.setVisible(extrusion or revolve)

    def _show_preview(self):
        self.canvas.finish_current_tool()
        self._collect_feature()
        self.workspace.setCurrentWidget(self.preview)
        self.preview.refresh_feature(self._feature)

    # -------------------------------------------------------------- lifecycle
    def accept(self):
        self.canvas.finish_current_tool()
        result = solve_sketch(self.canvas.sketch)
        self._update_solver_status(result)
        if not result.success:
            QMessageBox.warning(self, "Invalid sketch", result.message)
            return
        if not self.canvas.sketch.entities:
            QMessageBox.warning(
                self, "Empty sketch", "Create at least one sketch curve."
            )
            return
        self._collect_feature()
        if not self.preview.refresh_feature(self._feature):
            QMessageBox.warning(
                self,
                "Invalid feature",
                "The sketch cannot create valid geometry. Check open profiles, "
                "overlapping curves and revolve-axis crossings.",
            )
            self.view_preview.setChecked(True)
            self.workspace.setCurrentWidget(self.preview)
            return
        super().accept()

    def _on_sketch_changed(self):
        self._feature.sketch = self.canvas.snapshot()
        self._sync_constraints()

    def _solve_now(self):
        result = solve_sketch(self.canvas.sketch)
        self.canvas._rebuild_scene(solve=False)
        self.canvas.solver_changed.emit(result)
        self.canvas.sketch_changed.emit()

    def _update_solver_status(self, result):
        if result is None:
            self.status_label.setText("Sketch")
            return
        if not result.success:
            self.status_label.setText("Constraint conflict")
            self.status_label.setProperty("state", "error")
            self.status_label.setToolTip(result.message)
        elif result.fully_constrained:
            self.status_label.setText("Fully constrained")
            self.status_label.setProperty("state", "ok")
            self.status_label.setToolTip("0 remaining degrees of freedom")
        else:
            self.status_label.setText(
                f"Under-constrained · {result.degrees_of_freedom} DOF"
            )
            self.status_label.setProperty("state", "open")
            self.status_label.setToolTip(result.message)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _set_snap_enabled(self, enabled):
        self.snap_grid_check.setEnabled(bool(enabled))
        self.snap_geometry_check.setEnabled(bool(enabled))
        if enabled:
            self._snap_options_changed()
        else:
            self.canvas.sketch.snap_grid = False
            self.canvas.sketch.snap_geometry = False

    def _snap_options_changed(self):
        if not self.snap_action.isChecked():
            return
        self.canvas.sketch.snap_grid = self.snap_grid_check.isChecked()
        self.canvas.sketch.snap_geometry = self.snap_geometry_check.isChecked()

    # ------------------------------------------------------------- measurements
    @staticmethod
    def _entity(ref):
        return ref

    @staticmethod
    def _point(ref):
        if not isinstance(ref, SketchPoint):
            raise TypeError("Expected SketchPoint")
        return ref

    def _point_distance(self, first, second):
        a, b = self._point(first), self._point(second)
        return hypot(b.x - a.x, b.y - a.y)

    @staticmethod
    def _line_length(entity):
        if not isinstance(entity, SketchLine):
            return 1.0
        return hypot(
            entity.end.x - entity.start.x,
            entity.end.y - entity.start.y,
        )

    @staticmethod
    def _radius(entity):
        if isinstance(entity, SketchCircle):
            return abs(float(entity.radius))
        if isinstance(entity, SketchArc):
            return hypot(
                entity.start.x - entity.center.x,
                entity.start.y - entity.center.y,
            )
        return 1.0

    def _ask_value(
        self, title, default, *, allow_negative=False, maximum=1.0e12
    ):
        minimum = -maximum if allow_negative else 1.0e-9
        value, accepted = QInputDialog.getDouble(
            self,
            title,
            f"{title} value:",
            float(default),
            float(minimum),
            float(maximum),
            6,
        )
        return float(value) if accepted else None

    @staticmethod
    def _length_spin(parent):
        spin = QDoubleSpinBox(parent)
        spin.setRange(1.0e-9, 1.0e12)
        spin.setDecimals(6)
        spin.setSingleStep(1.0)
        return spin

    def _selection_warning(self, text):
        self.hint_label.setText(str(text))
        return False
