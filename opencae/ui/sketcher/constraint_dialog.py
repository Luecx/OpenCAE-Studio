"""Constraint-complete Sketcher dialog surface.

The base feature dialog owns the sketch actions and common editor behavior. This
specialization applies the complete selection policy and the public ribbon and
viewport chrome used by the actual OpenCAE Sketcher.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from opencae.model.entities.geometry import (
    SketchArc,
    SketchCircle,
    SketchConstraintKind,
    SketchLine,
)
from opencae.ui.core.icon_factory import IconKind
from opencae.ui.core.metrics import RIBBON_PAGE_HEIGHT
from opencae.ui.ribbon.ribbon_page import ResponsiveRibbonPage
from opencae.ui.ribbon.specs import RibbonGroupSpec
from opencae.ui.templates import ViewportToolButton

from .dialog import SketchFeatureDialog as _BaseSketchFeatureDialog


_DIMENSION_LAYOUT_KEY = "sketch_dimension_positions"


class SketchFeatureDialog(_BaseSketchFeatureDialog):
    """Feature editor with complete constraint policies and canonical ribbon."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The Arc popup is itself a visible ribbon button. Give it a generic
        # arc glyph instead of reusing the Center Arc glyph that appears inside
        # its menu, so every visible sketch command has a distinct icon.
        self._ribbon_actions["primitive.arc"].setIcon(
            self._icon(IconKind.SKETCH_ARC)
        )
        # The old curved undo/redo glyphs are visually busy at ribbon size.
        self._ribbon_actions["primitive.undo"].setIcon(
            self._icon(IconKind.PREVIOUS_FRAME)
        )
        self._ribbon_actions["primitive.redo"].setIcon(
            self._icon(IconKind.NEXT_FRAME)
        )

        layout = self._feature.parameters.get(_DIMENSION_LAYOUT_KEY)
        if not isinstance(layout, dict):
            layout = {}
            self._feature.parameters[_DIMENSION_LAYOUT_KEY] = layout
        self.canvas.set_dimension_layout(layout)
        self.canvas.dimension_edit_requested.connect(self._edit_dimension)

        # The base class wires Construction directly to the canvas. Replace
        # that connection with a guarded slot so selection-driven checked-state
        # synchronization can still repaint the QAction without converting the
        # selected geometry as a side effect.
        self._syncing_construction = False
        try:
            self.construction_action.toggled.disconnect()
        except TypeError:
            pass
        self.construction_action.toggled.connect(self._construction_toggled)

    def _build_ribbon_actions(self) -> None:
        """Expose dimensional commands as first-class ribbon actions."""
        super()._build_ribbon_actions()
        # Keep the generic Dimension QAction as a reusable menu entry for other
        # consumers, but the Sketcher ribbon itself owns a dedicated Dimensions
        # group with direct commands and no extra nesting layer.
        self._ribbon_actions.pop("constraint.dimension", None)
        for key, kind in (
            ("dimension.distance", "Distance"),
            ("dimension.horizontal", "DistanceX"),
            ("dimension.vertical", "DistanceY"),
            ("dimension.angle", "Angle"),
            ("dimension.radius", "Radius"),
            ("dimension.diameter", "Diameter"),
        ):
            self._register(key, self._dimension_actions[kind])

    def _build_ribbon(self):
        """Build the Sketcher ribbon with the same responsive rules as main UI."""

        groups = (
            RibbonGroupSpec(
                "SELECTION",
                (
                    "primitive.select",
                    "primitive.undo",
                    "primitive.redo",
                ),
                icon_action_id="primitive.select",
            ),
            RibbonGroupSpec(
                "PRIMITIVES",
                (
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
                ),
                icon_action_id="constraint.coincident",
            ),
            RibbonGroupSpec(
                "DIMENSIONS",
                (
                    "dimension.distance",
                    "dimension.horizontal",
                    "dimension.vertical",
                    "dimension.angle",
                    "dimension.radius",
                    "dimension.diameter",
                ),
                icon_action_id="dimension.distance",
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
        self.ribbon = ResponsiveRibbonPage(
            groups,
            self._ribbon_actions,
            parent=self,
        )
        self.ribbon.setObjectName("SketchRibbonHost")
        self.ribbon.setFixedHeight(RIBBON_PAGE_HEIGHT)
        return self.ribbon

    def _build_workspace(self, parent):
        """Build one main-window-style slim bar directly above the viewport."""
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

        self.view_sketch = ViewportToolButton("Sketch", checkable=True, parent=bar)
        self.view_preview = ViewportToolButton(
            "3D Preview", checkable=True, parent=bar
        )
        self.view_sketch.setChecked(True)
        self.view_group = QButtonGroup(bar)
        self.view_group.setExclusive(True)
        self.view_group.addButton(self.view_sketch)
        self.view_group.addButton(self.view_preview)
        row.addWidget(self.view_sketch)
        row.addWidget(self.view_preview)

        self.fit_button = ViewportToolButton("Fit", parent=bar)
        self.fit_button.setToolTip("Center and fit the sketch")
        row.addWidget(self.fit_button)
        row.addSpacing(8)

        self.status_label = QLabel("Ready", bar)
        self.status_label.setObjectName("SketchStatus")
        self.hint_label = QLabel("", bar)
        self.hint_label.setObjectName("SketchHint")
        row.addWidget(self.status_label)
        row.addWidget(self.hint_label)
        row.addStretch(1)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok,
            parent=bar,
        )
        self.buttons.setObjectName("SketchCommitButtons")
        ok = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok.setText(
            "Create Feature"
            if self.windowTitle().startswith("Create")
            else "Apply"
        )
        row.addWidget(self.buttons)
        layout.addWidget(bar)

        self.workspace = QStackedWidget(host)
        self.workspace.addWidget(self.canvas)
        self.workspace.addWidget(self.preview)
        layout.addWidget(self.workspace, 1)
        return host

    def _build_footer(self):
        """The Sketcher has no bottom command/status strip anymore."""
        footer = QWidget(self)
        footer.setFixedHeight(0)
        footer.hide()
        return footer

    def _construction_toggled(self, enabled: bool) -> None:
        if self._syncing_construction:
            return
        self.canvas.set_construction(bool(enabled))

    def _sync_construction_from_selection(self, _refs=None):
        entities = tuple(self.canvas.selected_entities())
        if not entities:
            return
        enabled = all(bool(getattr(entity, "construction", False)) for entity in entities)
        self._syncing_construction = True
        try:
            self.construction_action.setChecked(enabled)
        finally:
            self._syncing_construction = False
        self.canvas.construction = enabled

    def _edit_dimension(self, constraint) -> None:
        """Edit a selected driving dimension using the existing numeric editor."""

        if constraint is None or constraint.value is None:
            return
        kind = SketchConstraintKind.coerce(constraint.kind)
        title = {
            SketchConstraintKind.DISTANCE: "Distance",
            SketchConstraintKind.DISTANCE_X: "Horizontal distance",
            SketchConstraintKind.DISTANCE_Y: "Vertical distance",
            SketchConstraintKind.ANGLE: "Angle",
            SketchConstraintKind.RADIUS: "Radius",
            SketchConstraintKind.DIAMETER: "Diameter",
        }.get(kind)
        if title is None:
            return
        value = self._ask_value(
            f"Edit {title}",
            float(constraint.value),
            allow_negative=kind in {
                SketchConstraintKind.DISTANCE_X,
                SketchConstraintKind.DISTANCE_Y,
            },
            maximum=360.0 if kind is SketchConstraintKind.ANGLE else 1.0e12,
        )
        if value is None:
            return
        if self.canvas.set_dimension_value(constraint.id, value):
            self._sync_constraints()

    def _apply_constraint(self, kind: SketchConstraintKind | str):
        kind = SketchConstraintKind.coerce(kind)
        points = self.canvas.selected_points()
        entities = self.canvas.selected_entities()

        if kind is SketchConstraintKind.COLLINEAR:
            if len(entities) != 2 or not all(
                isinstance(entity, SketchLine) for entity in entities
            ):
                return self._selection_warning("Select exactly two lines")
            if self.canvas.add_constraint(kind, entities):
                self._sync_constraints()
            return

        if kind is SketchConstraintKind.POINT_ON_OBJECT:
            if len(points) != 1 or len(entities) != 1:
                return self._selection_warning(
                    "Select exactly one point and one line, circle or arc"
                )
            target = entities[0]
            if not isinstance(target, (SketchLine, SketchCircle, SketchArc)):
                return self._selection_warning(
                    "Point-on-object supports lines, circles and arcs"
                )
            if self.canvas.add_constraint(kind, (points[0], target)):
                self._sync_constraints()
            return

        if kind is SketchConstraintKind.SYMMETRY:
            if len(points) != 2 or len(entities) != 1:
                return self._selection_warning(
                    "Select two points and exactly one symmetry line"
                )
            if not isinstance(entities[0], SketchLine):
                return self._selection_warning("The symmetry axis must be a line")
            refs = (points[0], points[1], entities[0])
            if self.canvas.add_constraint(kind, refs):
                self._sync_constraints()
            return

        return super()._apply_constraint(kind)


__all__ = ["SketchFeatureDialog"]
