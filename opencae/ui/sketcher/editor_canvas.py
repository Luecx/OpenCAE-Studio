"""Sketcher-specific canvas polish layered on the reusable drafting surface."""

from __future__ import annotations

from copy import deepcopy
from math import hypot

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsSimpleTextItem

from opencae.model.entities.geometry import (
    SKETCH_ENTITY_TYPES,
    SketchArc,
    SketchCircle,
    SketchConstraintKind,
    SketchLine,
    SketchPoint,
    entity_points,
)
from opencae.sketch import constraint_label, solve_sketch

from .canvas import SketchCanvas, _ENTITY_ROLE, _EPS, _KIND_ROLE, _theme


_DIMENSION_KINDS = {
    SketchConstraintKind.DISTANCE,
    SketchConstraintKind.DISTANCE_X,
    SketchConstraintKind.DISTANCE_Y,
    SketchConstraintKind.ANGLE,
    SketchConstraintKind.RADIUS,
    SketchConstraintKind.DIAMETER,
}


class SketchEditorCanvas(SketchCanvas):
    """Use screen-stable labels and CAD-style dimension editing in the dialog."""

    dimension_edit_requested = pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        # ``SketchCanvas.__init__`` rebuilds the scene and therefore dispatches
        # into our overridden dimension renderer. Initialize all presentation
        # state before entering the base constructor.
        self._dimension_layout: dict[str, tuple[float, float]] = {}
        self._selected_dimension_id: str | None = None
        self._drag_dimension_id: str | None = None
        self._drag_dimension_moved = False
        super().__init__(*args, **kwargs)
        # QGraphicsView keeps hidden scroll ranges for panning, so disabling the
        # chrome does not remove middle-mouse navigation.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    # ------------------------------------------------------- sketch presentation
    def set_dimension_layout(self, layout: dict | None) -> None:
        """Bind persistent feature presentation metadata to this canvas.

        Dimension positions are UI presentation state rather than sketch
        topology, so they live in ``SketchFeature.parameters``. The mapping is
        keyed by the constraint's stable local identity and stores model-space
        coordinates only; no domain relationship is represented by the key.
        """

        self._dimension_layout = layout if isinstance(layout, dict) else {}
        self._rebuild_scene(solve=False)

    def set_construction(self, enabled: bool) -> None:
        """Apply construction state to selected entities as well as new geometry."""
        enabled = bool(enabled)
        selected = tuple(self.selected_entities())
        changed = tuple(
            entity
            for entity in selected
            if bool(getattr(entity, "construction", False)) != enabled
        )
        self.construction = enabled
        if changed:
            self._push_history()
            for entity in changed:
                entity.construction = enabled
            self._changed(solve=False)
        else:
            self.viewport().update()

    # ------------------------------------------------------------- dimensions
    def _constraint_by_id(self, constraint_id: str):
        for constraint in self.sketch.constraints:
            if constraint.id == constraint_id:
                return constraint
        return None

    @staticmethod
    def _is_dimension(constraint) -> bool:
        return constraint.kind in _DIMENSION_KINDS and constraint.value is not None

    def _dimension_at(self, viewport_point) -> str | None:
        item = self.itemAt(viewport_point)
        if item is None:
            return None
        if item.data(_KIND_ROLE) not in {"dimension", "dimension_line"}:
            return None
        value = str(item.data(_ENTITY_ROLE) or "")
        return value or None

    def _dimension_anchor_model(self, constraint) -> QPointF | None:
        anchor = self._constraint_anchor(constraint)
        if anchor is None:
            return None
        return QPointF(float(anchor.x()), float(-anchor.y()))

    def _dimension_direction(self, constraint) -> tuple[float, float] | None:
        refs = tuple(constraint.refs)
        if len(refs) >= 1 and isinstance(refs[0], SketchLine):
            line = refs[0]
            return line.end.x - line.start.x, line.end.y - line.start.y
        points = tuple(ref for ref in refs if isinstance(ref, SketchPoint))
        if len(points) >= 2:
            return points[1].x - points[0].x, points[1].y - points[0].y
        return None

    def _default_dimension_position(self, constraint, order: int) -> QPointF | None:
        """Place new dimensions outside sketch geometry instead of on top of it."""

        anchor = self._dimension_anchor_model(constraint)
        bounds = self.sketch.bounds()
        if anchor is None or bounds is None:
            return anchor
        xmin, ymin, xmax, ymax = (float(value) for value in bounds)
        cx = 0.5 * (xmin + xmax)
        cy = 0.5 * (ymin + ymax)
        # Stagger independent dimensions slightly while keeping the offset
        # screen-stable at the current zoom level.
        offset = self._pixels_to_scene(20.0 + 12.0 * (order % 4))
        kind = constraint.kind

        if kind in {SketchConstraintKind.RADIUS, SketchConstraintKind.DIAMETER}:
            # Radius/diameter callouts read most naturally outside the nearest
            # horizontal side of the whole profile.
            if anchor.x() >= cx:
                return QPointF(xmax + offset, anchor.y())
            return QPointF(xmin - offset, anchor.y())

        direction = self._dimension_direction(constraint)
        if kind is SketchConstraintKind.DISTANCE_X:
            horizontal = True
        elif kind is SketchConstraintKind.DISTANCE_Y:
            horizontal = False
        elif direction is not None:
            dx, dy = direction
            horizontal = abs(dx) >= abs(dy)
        else:
            horizontal = abs(anchor.y() - cy) >= abs(anchor.x() - cx)

        if horizontal:
            if anchor.y() >= cy:
                return QPointF(anchor.x(), ymax + offset)
            return QPointF(anchor.x(), ymin - offset)
        if anchor.x() >= cx:
            return QPointF(xmax + offset, anchor.y())
        return QPointF(xmin - offset, anchor.y())

    def _dimension_position(self, constraint, order: int) -> QPointF | None:
        stored = self._dimension_layout.get(constraint.id)
        if isinstance(stored, (tuple, list)) and len(stored) == 2:
            try:
                return QPointF(float(stored[0]), float(stored[1]))
            except (TypeError, ValueError):
                pass
        return self._default_dimension_position(constraint, order)

    def _draw_constraint_labels(self, _entity_map) -> None:
        dimension_order = 0
        for constraint in self.sketch.constraints:
            anchor = self._constraint_anchor(constraint)
            if anchor is None:
                continue

            if self._is_dimension(constraint):
                model_position = self._dimension_position(constraint, dimension_order)
                dimension_order += 1
                if model_position is None:
                    continue
                position = self._to_scene(model_position)

                leader = QPainterPath(anchor)
                leader.lineTo(position)
                leader_item = QGraphicsPathItem(leader)
                leader_pen = QPen(_theme("muted", "#98a2ad"))
                leader_pen.setCosmetic(True)
                leader_pen.setWidthF(1.0)
                leader_item.setPen(leader_pen)
                leader_item.setData(_ENTITY_ROLE, constraint.id)
                leader_item.setData(_KIND_ROLE, "dimension_line")
                leader_item.setZValue(8.0)
                self._scene.addItem(leader_item)

                item = QGraphicsSimpleTextItem(constraint_label(constraint))
                item.setData(_ENTITY_ROLE, constraint.id)
                item.setData(_KIND_ROLE, "dimension")
                item.setToolTip("Drag to reposition · double-click or Enter to edit")
                item.setBrush(_theme("accent", "#3296e6"))
                font = QFont()
                font.setPointSizeF(8.0)
                item.setFont(font)
                item.setFlag(
                    QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations,
                    True,
                )
                item.setPos(position)
                item.setZValue(10.0)
                self._scene.addItem(item)
                continue

            item = QGraphicsSimpleTextItem(constraint_label(constraint))
            item.setBrush(_theme("accent", "#3296e6"))
            font = QFont()
            font.setPointSizeF(8.0)
            item.setFont(font)
            item.setFlag(
                QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations,
                True,
            )
            item.setPos(
                anchor
                + QPointF(
                    self._pixels_to_scene(5.0),
                    -self._pixels_to_scene(5.0),
                )
            )
            item.setZValue(10.0)
            self._scene.addItem(item)

    def _sync_selection_style(self) -> None:
        super()._sync_selection_style()
        for item in self._scene.items():
            if item.data(_KIND_ROLE) != "dimension":
                continue
            selected = str(item.data(_ENTITY_ROLE) or "") == self._selected_dimension_id
            item.setBrush(
                _theme("accent_hover", "#53acef")
                if selected
                else _theme("accent", "#3296e6")
            )

    def clear_selection(self) -> None:
        self._selected_dimension_id = None
        super().clear_selection()

    def set_dimension_value(self, constraint_or_id, value: float) -> bool:
        """Edit one driving dimension with solver validation and undo support."""

        constraint_id = str(getattr(constraint_or_id, "id", constraint_or_id) or "")
        constraint = self._constraint_by_id(constraint_id)
        if constraint is None or not self._is_dimension(constraint):
            return False

        before = deepcopy(self.sketch)
        constraint.value = float(value)
        result = solve_sketch(self.sketch)
        if not result.success:
            self.sketch = before
            self._last_solve = solve_sketch(self.sketch)
            self._rebuild_scene(solve=False)
            self.solver_changed.emit(result)
            self.status_message.emit(result.message)
            return False

        self._history.append(before)
        if len(self._history) > 100:
            self._history.pop(0)
        self._future.clear()
        self._last_solve = result
        self._rebuild_scene(solve=False)
        self._selected_dimension_id = constraint_id
        self._sync_selection_style()
        self.solver_changed.emit(result)
        self.sketch_changed.emit()
        return True

    def _delete_selected_dimension(self) -> bool:
        constraint_id = self._selected_dimension_id
        if not constraint_id:
            return False
        if self._constraint_by_id(constraint_id) is None:
            self._selected_dimension_id = None
            return False
        self._push_history()
        self.sketch.constraints = [
            constraint
            for constraint in self.sketch.constraints
            if constraint.id != constraint_id
        ]
        self._selected_dimension_id = None
        self._changed(solve=True)
        return True

    # ------------------------------------------------------------- interaction
    def mousePressEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.tool == "Select"
        ):
            constraint_id = self._dimension_at(event.position().toPoint())
            if constraint_id:
                self._selected_entities.clear()
                self._selected_points.clear()
                self._selected_dimension_id = constraint_id
                self._drag_dimension_id = constraint_id
                self._drag_dimension_moved = False
                self._sync_selection_style()
                self.selection_changed.emit(())
                self.status_message.emit(
                    "Drag dimension to reposition · double-click or Enter to edit"
                )
                event.accept()
                return
            self._selected_dimension_id = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_dimension_id:
            model = self._event_model_point(event)
            self._dimension_layout[self._drag_dimension_id] = (
                float(model.x()),
                float(model.y()),
            )
            self._drag_dimension_moved = True
            selected = self._drag_dimension_id
            self._rebuild_scene(solve=False)
            self._selected_dimension_id = selected
            self._sync_selection_style()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._drag_dimension_id
        ):
            moved = self._drag_dimension_moved
            self._drag_dimension_id = None
            self._drag_dimension_moved = False
            if moved:
                # The layout mapping is directly bound to persistent feature
                # presentation metadata, so this signal only refreshes clients.
                self.sketch_changed.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.tool == "Select"
        ):
            constraint_id = self._dimension_at(event.position().toPoint())
            constraint = self._constraint_by_id(constraint_id or "")
            if constraint is not None and self._is_dimension(constraint):
                self._selected_dimension_id = constraint.id
                self._sync_selection_style()
                self.dimension_edit_requested.emit(constraint)
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        if self._selected_dimension_id and event.key() in {
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        }:
            constraint = self._constraint_by_id(self._selected_dimension_id)
            if constraint is not None:
                self.dimension_edit_requested.emit(constraint)
            event.accept()
            return
        if (
            self._selected_dimension_id
            and event.key() in {Qt.Key.Key_Delete, Qt.Key.Key_Backspace}
            and self._delete_selected_dimension()
        ):
            event.accept()
            return
        super().keyPressEvent(event)

    # ------------------------------------------------------------------ axes
    def _draw_axes(self, painter: QPainter, rect, major: float) -> None:
        """Draw axes in scene space but labels at a fixed, restrained screen size."""
        painter.save()
        x_pen = QPen(_theme("axis_x", "#de6a62"))
        y_pen = QPen(_theme("axis_y", "#66b56f"))
        x_pen.setCosmetic(True)
        y_pen.setCosmetic(True)
        x_pen.setWidthF(1.6 if self.show_revolve_axis else 1.15)
        y_pen.setWidthF(1.15)
        if self.show_revolve_axis:
            x_pen.setStyle(Qt.PenStyle.DashDotLine)
        painter.setPen(x_pen)
        painter.drawLine(QPointF(rect.left(), 0.0), QPointF(rect.right(), 0.0))
        painter.setPen(y_pen)
        painter.drawLine(QPointF(0.0, rect.top()), QPointF(0.0, rect.bottom()))
        painter.restore()

        painter.save()
        painter.resetTransform()
        text_color = _theme("muted", "#98a2ad")
        text_color.setAlpha(175)
        text_pen = QPen(text_color)
        text_pen.setCosmetic(True)
        painter.setPen(text_pen)
        font = QFont(painter.font())
        font.setPixelSize(10)
        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)

        viewport = self.viewport().rect()
        x_axis_y = self.mapFromScene(QPointF(0.0, 0.0)).y()
        y_axis_x = self.mapFromScene(QPointF(0.0, 0.0)).x()

        for index in range(int(rect.left() // major) - 1, int(rect.right() // major) + 2):
            if not index:
                continue
            value = index * major
            screen = self.mapFromScene(QPointF(value, 0.0))
            if -40 <= screen.x() <= viewport.width() + 40:
                painter.drawText(screen.x() + 4, x_axis_y - 4, f"{value:g}")

        model_min_y = -rect.bottom()
        model_max_y = -rect.top()
        for index in range(int(model_min_y // major) - 1, int(model_max_y // major) + 2):
            if not index:
                continue
            value = index * major
            screen = self.mapFromScene(QPointF(0.0, -value))
            if -20 <= screen.y() <= viewport.height() + 20:
                painter.drawText(y_axis_x + 5, screen.y() - 3, f"{value:g}")

        if self.show_revolve_axis:
            axis_color = _theme("axis_x", "#de6a62")
            axis_color.setAlpha(190)
            painter.setPen(QPen(axis_color))
            painter.drawText(10, max(13, x_axis_y - 7), "REVOLVE AXIS  X")
        painter.restore()


__all__ = ["SketchEditorCanvas"]
