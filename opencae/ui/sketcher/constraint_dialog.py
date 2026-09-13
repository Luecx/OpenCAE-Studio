"""Constraint-complete Sketcher dialog surface.

The base feature dialog owns the general sketch/feature workspace. This small
specialization keeps selection policy for the less common geometric constraints
separate from the already large UI scaffold while exposing the same
``SketchFeatureDialog`` public API through ``opencae.ui.sketcher``.
"""

from __future__ import annotations

from opencae.model.entities.geometry import SketchArc, SketchCircle, SketchLine
from opencae.ui.core.icon_factory import IconKind, make_icon

from .dialog import SketchFeatureDialog as _BaseSketchFeatureDialog


class SketchFeatureDialog(_BaseSketchFeatureDialog):
    """Feature editor with the complete solver constraint surface exposed."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_toolbar_icons()
        self._add_extended_constraint_actions()

    def _apply_toolbar_icons(self) -> None:
        tool_icons = {
            "Select": IconKind.SKETCH_SELECT,
            "Point": IconKind.SKETCH_POINT,
            "Line": IconKind.SKETCH_LINE,
            "Polyline": IconKind.SKETCH_POLYLINE,
            "Rectangle": IconKind.SKETCH_RECTANGLE,
            "Circle": IconKind.SKETCH_CIRCLE,
            "Center Arc": IconKind.SKETCH_ARC,
            "3-Point Arc": IconKind.SKETCH_ARC,
            "Ellipse": IconKind.SKETCH_ELLIPSE,
            "Spline": IconKind.SKETCH_SPLINE,
            "Slot": IconKind.SKETCH_SLOT,
        }
        for tool, kind in tool_icons.items():
            action = self._tool_actions.get(tool)
            if action is not None:
                action.setIcon(make_icon(kind, 18))

        self.construction_action.setIcon(
            make_icon(IconKind.SKETCH_CONSTRUCTION, 18)
        )
        for action in self.toolbar.actions():
            if action.property("constraintKind"):
                action.setIcon(make_icon(IconKind.SKETCH_CONSTRAINT, 18))
            elif action.property("dimensionKind"):
                action.setIcon(make_icon(IconKind.SKETCH_DIMENSION, 18))

    def _add_extended_constraint_actions(self) -> None:
        self.toolbar.addSeparator()
        for label, kind in (
            ("Collinear", "Collinear"),
            ("Point on", "Point on object"),
            ("Symmetry", "Symmetry"),
        ):
            action = self.toolbar.addAction(
                make_icon(IconKind.SKETCH_CONSTRAINT, 18),
                label,
            )
            action.setProperty("constraintKind", kind)
            action.triggered.connect(
                lambda _checked=False, value=kind: self._apply_constraint(value)
            )

    def _apply_constraint(self, kind: str):
        points = tuple(
            f"point:{value}" for value in self.canvas.selected_point_ids()
        )
        entities = tuple(
            f"entity:{value}" for value in self.canvas.selected_entity_ids()
        )

        if kind == "Collinear":
            if len(entities) != 2 or not all(
                isinstance(self._entity(ref), SketchLine) for ref in entities
            ):
                return self._selection_warning("Select exactly two lines")
            if self.canvas.add_constraint(kind, entities):
                self._sync_constraints()
            return

        if kind == "Point on object":
            if len(points) != 1 or len(entities) != 1:
                return self._selection_warning(
                    "Select exactly one point and one line, circle or arc"
                )
            target = self._entity(entities[0])
            if not isinstance(target, (SketchLine, SketchCircle, SketchArc)):
                return self._selection_warning(
                    "Point-on-object supports lines, circles and arcs"
                )
            if self.canvas.add_constraint(kind, (points[0], entities[0])):
                self._sync_constraints()
            return

        if kind == "Symmetry":
            if len(points) != 2 or len(entities) != 1:
                return self._selection_warning(
                    "Select two points and exactly one symmetry line"
                )
            if not isinstance(self._entity(entities[0]), SketchLine):
                return self._selection_warning("The symmetry axis must be a line")
            refs = (points[0], points[1], entities[0])
            if self.canvas.add_constraint(kind, refs):
                self._sync_constraints()
            return

        return super()._apply_constraint(kind)


__all__ = ["SketchFeatureDialog"]
