"""Constraint-complete Sketcher dialog surface.

The base feature dialog owns the sketch actions and common editor behavior. This
specialization applies the complete selection policy and the public ribbon
layout used by the actual OpenCAE Sketcher.
"""

from __future__ import annotations

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

from .dialog import SketchFeatureDialog as _BaseSketchFeatureDialog


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

    def _build_ribbon(self):
        """Build the Sketcher ribbon with the same responsive rules as main UI.

        The ordinary :class:`ResponsiveRibbonPage` deliberately collapses the
        widest group first and continues only until the available width is
        satisfied. Keeping the Sketcher on that exact implementation avoids a
        separate all-or-nothing narrow mode and makes resize behavior identical
        to the main OpenCAE ribbon.
        """

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
                    # Keep the driving-dimension entry first so it remains
                    # immediately discoverable when the group is collapsed.
                    "constraint.dimension",
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
                icon_action_id="constraint.dimension",
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
