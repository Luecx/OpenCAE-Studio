"""OpenCAE-styled parametric sketch and feature editor."""

from __future__ import annotations

from copy import deepcopy
from math import hypot

from PyQt6.QtCore import QSignalBlocker, Qt
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QSplitter,
    QStackedWidget,
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
from opencae.ui.core.metrics import RIBBON_ICON_SIZE, RIBBON_PAGE_HEIGHT
from opencae.ui.primitives.buttons import (
    ButtonFormAction,
    ButtonFormDanger,
    ButtonViewportAction,
    ButtonViewportToggle,
)
from opencae.ui.primitives.checks import CheckForm
from opencae.ui.primitives.inputs import InputFormNumber, InputFormText
from opencae.ui.primitives.labels import LabelForm, LabelGroup, LabelMuted, LabelStatus
from opencae.ui.primitives.lists import ListForm
from opencae.ui.primitives.selects import SelectForm
from opencae.ui.primitives.separators import SeparatorHorizontal
from opencae.ui.ribbon.ribbon_page import ResponsiveRibbonPage
from opencae.ui.ribbon.specs import RibbonGroupSpec

from .editor_canvas import SketchEditorCanvas
from .preview import SketchFeaturePreview


class _SketchResponsiveRibbonPage(ResponsiveRibbonPage):
    """Use the main ribbon collapse model with a clean three-button narrow state."""

    def _target_collapsed_groups(self, available_width):
        target = super()._target_collapsed_groups(available_width)
        if len(target) >= 2:
            return frozenset(spec.title for spec in self._specs)
        return target


class SketchFeatureDialog(QDialog):
    """Large modal feature editor with the same ribbon metrics as the main window."""

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
        self._ribbon_actions: dict[str, QAction] = {}
        self._constraint_actions: dict[str, QAction] = {}
        self._dimension_actions: dict[str, QAction] = {}

        self.canvas = SketchEditorCanvas(self._feature.sketch, self)
        self.preview = SketchFeaturePreview(self)
        self._build_ribbon_actions()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_ribbon())

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setObjectName("SketchWorkspaceSplitter")
        splitter.addWidget(self._build_workspace(splitter))
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
    def _icon(self, kind: IconKind):
        return make_icon(kind, RIBBON_ICON_SIZE)

    def _register(self, key: str, action: QAction) -> QAction:
        self._ribbon_actions[key] = action
        return action

    def _tool_action(self, key: str, tool: str, label: str, icon_kind: IconKind):
        action = QAction(self._icon(icon_kind), label, self)
        action.setCheckable(True)
        action.setData(tool)
        action.triggered.connect(
            lambda checked=False, value=tool: (
                self.canvas.set_tool(value) if checked else None
            )
        )
        self._tool_group.addAction(action)
        self._tool_actions[tool] = action
        self._register(key, action)
        return action

    def _menu_action(self, key: str, label: str, icon_kind: IconKind) -> QAction:
        action = QAction(self._icon(icon_kind), label, self)
        action.setMenu(QMenu(self))
        self._register(key, action)
        return action

    def _constraint_action(
        self,
        key: str,
        label: str,
        kind: str,
        icon_kind: IconKind,
        *,
        ribbon: bool = True,
    ) -> QAction:
        action = QAction(self._icon(icon_kind), label, self)
        action.setProperty("constraintKind", kind)
        action.triggered.connect(
            lambda _checked=False, value=kind: self._apply_constraint(value)
        )
        self._constraint_actions[kind] = action
        if ribbon:
            self._register(key, action)
        return action

    def _dimension_action(
        self,
        label: str,
        kind: str,
        icon_kind: IconKind,
    ) -> QAction:
        action = QAction(self._icon(icon_kind), label, self)
        action.setProperty("dimensionKind", kind)
        action.triggered.connect(
            lambda _checked=False, value=kind: self._apply_dimension(value)
        )
        self._dimension_actions[kind] = action
        return action

    def _build_ribbon_actions(self) -> None:
        self._tool_group = QActionGroup(self)
        self._tool_group.setExclusive(True)

        self._tool_action(
            "primitive.select", "Select", "Select", IconKind.SKETCH_SELECT
        )

        undo = QAction(self._icon(IconKind.UNDO), "Undo", self)
        undo.triggered.connect(lambda _checked=False: self.canvas.undo())
        self._register("primitive.undo", undo)
        redo = QAction(self._icon(IconKind.REDO), "Redo", self)
        redo.triggered.connect(lambda _checked=False: self.canvas.redo())
        self._register("primitive.redo", redo)

        for key, tool, label, icon_kind in (
            ("primitive.point", "Point", "Point", IconKind.SKETCH_POINT),
            ("primitive.line", "Line", "Line", IconKind.SKETCH_LINE),
            ("primitive.polyline", "Polyline", "Polyline", IconKind.SKETCH_POLYLINE),
            ("primitive.rectangle", "Rectangle", "Rectangle", IconKind.SKETCH_RECTANGLE),
            ("primitive.circle", "Circle", "Circle", IconKind.SKETCH_CIRCLE),
        ):
            self._tool_action(key, tool, label, icon_kind)

        arc = self._menu_action("primitive.arc", "Arc", IconKind.SKETCH_ARC_CENTER)
        center_arc = self._tool_action(
            "_menu.center_arc",
            "Center Arc",
            "Center Arc",
            IconKind.SKETCH_ARC_CENTER,
        )
        three_point_arc = self._tool_action(
            "_menu.three_point_arc",
            "3-Point Arc",
            "3-Point Arc",
            IconKind.SKETCH_ARC_3POINT,
        )
        self._ribbon_actions.pop("_menu.center_arc", None)
        self._ribbon_actions.pop("_menu.three_point_arc", None)
        arc.menu().addAction(center_arc)
        arc.menu().addAction(three_point_arc)

        more_primitives = self._menu_action(
            "primitive.more", "More", IconKind.SKETCH_PRIMITIVES_MORE
        )
        for tool, label, icon_kind in (
            ("Ellipse", "Ellipse", IconKind.SKETCH_ELLIPSE),
            ("Spline", "Spline", IconKind.SKETCH_SPLINE),
            ("Slot", "Slot", IconKind.SKETCH_SLOT),
        ):
            action = self._tool_action(
                f"_menu.{tool.lower()}", tool, label, icon_kind
            )
            self._ribbon_actions.pop(f"_menu.{tool.lower()}", None)
            more_primitives.menu().addAction(action)

        self._tool_actions["Select"].setChecked(True)

        for key, label, kind, icon_kind in (
            ("constraint.coincident", "Coincident", "Coincident", IconKind.SKETCH_CONSTRAINT_COINCIDENT),
            ("constraint.horizontal", "Horizontal", "Horizontal", IconKind.SKETCH_CONSTRAINT_HORIZONTAL),
            ("constraint.vertical", "Vertical", "Vertical", IconKind.SKETCH_CONSTRAINT_VERTICAL),
            ("constraint.parallel", "Parallel", "Parallel", IconKind.SKETCH_CONSTRAINT_PARALLEL),
            ("constraint.perpendicular", "Perp.", "Perpendicular", IconKind.SKETCH_CONSTRAINT_PERPENDICULAR),
            ("constraint.tangent", "Tangent", "Tangent", IconKind.SKETCH_CONSTRAINT_TANGENT),
            ("constraint.equal", "Equal", "Equal", IconKind.SKETCH_CONSTRAINT_EQUAL),
            ("constraint.fixed", "Fixed", "Fixed", IconKind.SKETCH_CONSTRAINT_FIXED),
        ):
            self._constraint_action(key, label, kind, icon_kind)

        more_constraints = self._menu_action(
            "constraint.more", "More", IconKind.SKETCH_CONSTRAINT_MORE
        )
        for label, kind, icon_kind in (
            ("Concentric", "Concentric", IconKind.SKETCH_CONSTRAINT_CONCENTRIC),
            ("Midpoint", "Midpoint", IconKind.SKETCH_CONSTRAINT_MIDPOINT),
            ("Collinear", "Collinear", IconKind.SKETCH_CONSTRAINT_COLLINEAR),
            ("Point on", "Point on object", IconKind.SKETCH_CONSTRAINT_POINT_ON),
            ("Symmetry", "Symmetry", IconKind.SKETCH_CONSTRAINT_SYMMETRY),
        ):
            action = self._constraint_action(
                f"_menu.constraint.{kind}", label, kind, icon_kind, ribbon=False
            )
            more_constraints.menu().addAction(action)

        self.dimension_action = self._menu_action(
            "constraint.dimension", "Dimension", IconKind.SKETCH_DIMENSION
        )
        for label, kind, icon_kind in (
            ("Distance", "Distance", IconKind.SKETCH_DIMENSION_DISTANCE),
            ("Horizontal", "DistanceX", IconKind.SKETCH_DIMENSION_HORIZONTAL),
            ("Vertical", "DistanceY", IconKind.SKETCH_DIMENSION_VERTICAL),
            ("Angle", "Angle", IconKind.SKETCH_DIMENSION_ANGLE),
            ("Radius", "Radius", IconKind.SKETCH_DIMENSION_RADIUS),
            ("Diameter", "Diameter", IconKind.SKETCH_DIMENSION_DIAMETER),
        ):
            self.dimension_action.menu().addAction(
                self._dimension_action(label, kind, icon_kind)
            )

        self.construction_action = QAction(
            self._icon(IconKind.SKETCH_CONSTRUCTION), "Construction", self
        )
        self.construction_action.setCheckable(True)
        self._register("options.construction", self.construction_action)

        self.grid_action = QAction(self._icon(IconKind.SKETCH_GRID), "Grid", self)
        self.grid_action.setCheckable(True)
        self.grid_action.setChecked(True)
        self._register("options.grid", self.grid_action)

        self.snap_action = QAction(self._icon(IconKind.SKETCH_SNAP), "Snap", self)
        self.snap_action.setCheckable(True)
        self.snap_action.setChecked(True)
        self._register("options.snap", self.snap_action)

    def _build_ribbon(self):
        groups = (
            RibbonGroupSpec(
                "PRIMITIVES",
                (
                    "primitive.select",
                    "primitive.undo",
                    "primitive.redo",
                    "primitive.point",
                    "primitive.line",
                    "primitive.polyline",
                    "primitive.rectangle",
                    "primitive.circle",
                    "primitive.arc",
                    "primitive.more",
                ),
                icon_action_id="primitive.line",
            ),
            RibbonGroupSpec(
                "CONSTRAINTS",
                (
                    "constraint.coincident",
                    "constraint.horizontal",
                    "constraint.vertical",
                    "constraint.parallel",
                    "constraint.perpendicular",
                    "constraint.tangent",
                    "constraint.equal",
                    "constraint.fixed",
                    "constraint.more",
                    "constraint.dimension",
                ),
                icon_action_id="constraint.coincident",
            ),
            RibbonGroupSpec(
                "CONSTRUCTION/GRID",
                (
                    "options.construction",
                    "options.grid",
                    "options.snap",
                ),
                icon_action_id="options.construction",
            ),
        )
        self.ribbon = _SketchResponsiveRibbonPage(
            groups,
            self._ribbon_actions,
            parent=self,
        )
        self.ribbon.setObjectName("SketchRibbonHost")
        self.ribbon.setFixedHeight(RIBBON_PAGE_HEIGHT)
        return self.ribbon

    def _build_workspace(self, parent):
        host = QWidget(parent)
        host.setObjectName("SketchViewportHost")
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        bar = QWidget(host)
        bar.setObjectName("ViewportToolbar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 5, 8, 5)
        row.setSpacing(4)

        self.view_sketch = ButtonViewportToggle(
            "Sketch", checked=True, parent=bar
        )
        self.view_preview = ButtonViewportToggle("3D Preview", parent=bar)
        self.view_group = QButtonGroup(bar)
        self.view_group.setExclusive(True)
        self.view_group.addButton(self.view_sketch)
        self.view_group.addButton(self.view_preview)
        row.addWidget(self.view_sketch)
        row.addWidget(self.view_preview)
        row.addStretch(1)
        self.fit_button = ButtonViewportAction(
            "Fit", tooltip="Center and fit the sketch", parent=bar
        )
        row.addWidget(self.fit_button)
        layout.addWidget(bar)

        self.workspace = QStackedWidget(host)
        self.workspace.addWidget(self.canvas)
        self.workspace.addWidget(self.preview)
        layout.addWidget(self.workspace, 1)
        return host

    def _build_inspector(self, parent):
        panel = QFrame(parent)
        panel.setObjectName("SketchInspector")
        panel.setMinimumWidth(250)
        panel.setMaximumWidth(360)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = LabelGroup("FEATURE", panel)
        title.setObjectName("SketchInspectorHeading")
        layout.addWidget(title)
        layout.addWidget(LabelForm("Name", panel))
        self.name_edit = InputFormText(parent=panel)
        layout.addWidget(self.name_edit)
        layout.addWidget(LabelForm("Type", panel))
        self.mode_combo = SelectForm(panel)
        self.mode_combo.addItems(tuple(mode.value for mode in SketchFeatureMode))
        layout.addWidget(self.mode_combo)
        layout.addWidget(LabelForm("Operation", panel))
        self.operation_combo = SelectForm(panel)
        self.operation_combo.addItems(("New", "Add", "Cut", "Intersect"))
        layout.addWidget(self.operation_combo)

        self.depth_label = LabelForm("Depth", panel)
        self.depth_spin = self._length_spin(panel)
        self.angle_label = LabelForm("Angle", panel)
        self.angle_spin = InputFormNumber(
            minimum=0.001,
            maximum=360.0,
            decimals=3,
            step=5.0,
            suffix="°",
            parent=panel,
        )
        layout.addWidget(self.depth_label)
        layout.addWidget(self.depth_spin)
        layout.addWidget(self.angle_label)
        layout.addWidget(self.angle_spin)

        self.symmetric_check = CheckForm(
            "Symmetric about sketch plane", parent=panel
        )
        self.reverse_check = CheckForm("Reverse direction", parent=panel)
        layout.addWidget(self.symmetric_check)
        layout.addWidget(self.reverse_check)
        self.axis_note = LabelMuted(
            "Revolve axis: X axis\nShown dash-dot in the sketch.", panel
        )
        self.axis_note.setObjectName("SketchAxisNote")
        self.axis_note.setWordWrap(True)
        layout.addWidget(self.axis_note)

        layout.addWidget(SeparatorHorizontal(panel))
        constraints_title = LabelGroup("CONSTRAINTS & DIMENSIONS", panel)
        constraints_title.setObjectName("SketchInspectorHeading")
        layout.addWidget(constraints_title)
        self.constraint_list = ListForm(
            object_name="SketchConstraintList",
            parent=panel,
        )
        layout.addWidget(self.constraint_list, 1)
        constraint_row = QHBoxLayout()
        self.delete_constraint_button = ButtonFormDanger("Remove", panel)
        self.solve_button = ButtonFormAction("Solve", parent=panel)
        constraint_row.addWidget(self.delete_constraint_button)
        constraint_row.addWidget(self.solve_button)
        layout.addLayout(constraint_row)

        layout.addWidget(SeparatorHorizontal(panel))
        options_title = LabelGroup("SKETCH OPTIONS", panel)
        options_title.setObjectName("SketchInspectorHeading")
        layout.addWidget(options_title)
        self.auto_constraints_check = CheckForm(
            "Automatic H/V constraints", checked=True, parent=panel
        )
        self.snap_grid_check = CheckForm(
            "Snap to grid",
            checked=self.canvas.sketch.snap_grid,
            parent=panel,
        )
        self.snap_geometry_check = CheckForm(
            "Snap to geometry",
            checked=self.canvas.sketch.snap_geometry,
            parent=panel,
        )
        self.show_dimensions_check = CheckForm(
            "Show dimensions", checked=True, parent=panel
        )
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
        self.status_label = LabelStatus(
            "Ready", object_name="SketchStatus", parent=footer
        )
        self.hint_label = LabelMuted("", footer)
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
        self.fit_button.clicked.connect(self._fit_current_view)
        self.construction_action.toggled.connect(self.canvas.set_construction)
        self.grid_action.toggled.connect(self.canvas.set_grid_visible)
        self.snap_action.toggled.connect(self._set_snap_enabled)
        self.canvas.sketch_changed.connect(self._on_sketch_changed)
        self.canvas.selection_changed.connect(self._sync_construction_from_selection)
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

    def _fit_current_view(self):
        if self.workspace.currentWidget() is self.canvas:
            self.canvas.fit_sketch()
            return
        fit = getattr(self.preview, "fit_view", None)
        if callable(fit):
            fit()

    def _sync_construction_from_selection(self, _refs=None):
        entities = tuple(self.canvas.selected_entities())
        if not entities:
            return
        enabled = all(bool(getattr(entity, "construction", False)) for entity in entities)
        blocker = QSignalBlocker(self.construction_action)
        self.construction_action.setChecked(enabled)
        del blocker
        self.canvas.construction = enabled

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
            value = self._ask_value(title, default, allow_negative=True)
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
        return InputFormNumber(
            minimum=1.0e-9,
            maximum=1.0e12,
            decimals=6,
            step=1.0,
            parent=parent,
        )

    def _selection_warning(self, text):
        self.hint_label.setText(str(text))
        return False
