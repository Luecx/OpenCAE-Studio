"""Interactive, theme-aware 2D drafting surface for OpenCAE sketches."""

from __future__ import annotations

from copy import deepcopy
from math import atan2, cos, hypot, log10, pi, sin

from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeySequence, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
)

from opencae.model.entities.geometry import (
    SketchArc,
    SketchCircle,
    SketchConstraint,
    SketchDefinition,
    SketchEllipse,
    SketchLine,
    SketchPoint,
    SketchSpline,
)
from opencae.sketch import constraint_label, solve_sketch
from opencae.ui.core.theme import PALETTE

_EPS = 1.0e-9
_ENTITY_ROLE = 0
_KIND_ROLE = 1


def _theme(name: str, fallback: str) -> QColor:
    return QColor(str(PALETTE.get(name, fallback)))


def _distance(a: QPointF, b: QPointF) -> float:
    return hypot(float(a.x() - b.x()), float(a.y() - b.y()))


class _OrderedSelection:
    """Small insertion-ordered set used for deterministic CAD selections."""

    def __init__(self, values=()):
        self._values = dict.fromkeys(str(value) for value in values if str(value))

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def __contains__(self, value):
        return str(value) in self._values

    def add(self, value) -> None:
        value = str(value)
        if value:
            self._values[value] = None

    def remove(self, value) -> None:
        del self._values[str(value)]

    def discard(self, value) -> None:
        self._values.pop(str(value), None)

    def clear(self) -> None:
        self._values.clear()


class SketchCanvas(QGraphicsView):
    """CAD-like 2D sketch canvas backed directly by ``SketchDefinition``."""

    sketch_changed = pyqtSignal()
    selection_changed = pyqtSignal(object)
    solver_changed = pyqtSignal(object)
    status_message = pyqtSignal(str)

    DRAW_TOOLS = {
        "Select",
        "Point",
        "Line",
        "Polyline",
        "Rectangle",
        "Circle",
        "Center Arc",
        "3-Point Arc",
        "Ellipse",
        "Spline",
        "Slot",
    }

    def __init__(self, sketch: SketchDefinition | None = None, parent=None):
        super().__init__(parent)
        self.sketch = sketch or SketchDefinition()
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setObjectName("SketchCanvas")
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

        self.tool = "Select"
        self.construction = False
        self.auto_constraints = True
        self.show_grid = True
        self.show_dimensions = True
        self.show_points = True
        self.show_revolve_axis = False

        self._selected_entities = _OrderedSelection()
        self._selected_points = _OrderedSelection()
        self._history: list[SketchDefinition] = []
        self._future: list[SketchDefinition] = []
        self._tool_points: list[tuple[QPointF, str | None]] = []
        self._spline_points: list[tuple[QPointF, str | None]] = []
        self._rubber_point: QPointF | None = None
        self._drag_point_id: str | None = None
        self._drag_last_valid: SketchDefinition | None = None
        self._panning = False
        self._pan_start = QPoint()
        self._last_solve = None

        self._rebuild_scene(solve=True)
        self.fit_sketch()

    # ---------------------------------------------------------------- settings
    def set_tool(self, name: str) -> None:
        name = str(name)
        if name not in self.DRAW_TOOLS:
            name = "Select"
        if self.tool != name:
            self.cancel_tool()
        self.tool = name
        self.status_message.emit(self._tool_hint(name))
        self.viewport().update()

    def set_construction(self, enabled: bool) -> None:
        self.construction = bool(enabled)
        self.viewport().update()

    def set_grid_visible(self, enabled: bool) -> None:
        self.show_grid = bool(enabled)
        self.viewport().update()

    def set_dimensions_visible(self, enabled: bool) -> None:
        self.show_dimensions = bool(enabled)
        self._rebuild_scene(solve=False)

    def set_revolve_axis_visible(self, enabled: bool) -> None:
        """Highlight the X axis as the fixed revolve axis when required."""
        self.show_revolve_axis = bool(enabled)
        self.viewport().update()

    # -------------------------------------------------------------- selection
    def selected_entity_ids(self) -> tuple[str, ...]:
        return tuple(self._selected_entities)

    def selected_point_ids(self) -> tuple[str, ...]:
        return tuple(self._selected_points)

    def selected_refs(self) -> tuple[str, ...]:
        return tuple(f"point:{value}" for value in self._selected_points) + tuple(
            f"entity:{value}" for value in self._selected_entities
        )

    def clear_selection(self) -> None:
        self._selected_entities.clear()
        self._selected_points.clear()
        self._sync_selection_style()
        self.selection_changed.emit(())

    def select_all(self) -> None:
        self._selected_entities = _OrderedSelection(
            str(getattr(entity, "id", "")) for entity in self.sketch.entities
        )
        self._selected_points = _OrderedSelection(
            point.id for point in self.sketch.points
        )
        self._sync_selection_style()
        self.selection_changed.emit(self.selected_refs())

    # --------------------------------------------------------------- commands
    def snapshot(self) -> SketchDefinition:
        return deepcopy(self.sketch)

    def _push_history(self) -> None:
        self._history.append(deepcopy(self.sketch))
        if len(self._history) > 100:
            self._history.pop(0)
        self._future.clear()

    def undo(self) -> None:
        if not self._history:
            return
        self._future.append(deepcopy(self.sketch))
        self.sketch = self._history.pop()
        self._selection_reset_after_history()

    def redo(self) -> None:
        if not self._future:
            return
        self._history.append(deepcopy(self.sketch))
        self.sketch = self._future.pop()
        self._selection_reset_after_history()

    def _selection_reset_after_history(self) -> None:
        self._selected_entities.clear()
        self._selected_points.clear()
        self._drag_point_id = None
        self._drag_last_valid = None
        self.cancel_tool()
        self._rebuild_scene(solve=True)
        self.sketch_changed.emit()
        self.selection_changed.emit(())

    def delete_selected(self) -> None:
        entity_ids = set(self._selected_entities)
        point_ids = set(self._selected_points)
        if not entity_ids and not point_ids:
            return
        self._push_history()
        kept = []
        for entity in self.sketch.entities:
            refs = set(_entity_point_ids(entity))
            entity_id = str(getattr(entity, "id", ""))
            if entity_id in entity_ids or refs.intersection(point_ids):
                entity_ids.add(entity_id)
                point_ids.update(refs)
            else:
                kept.append(entity)
        self.sketch.entities = kept
        used = {point_id for entity in kept for point_id in _entity_point_ids(entity)}
        self.sketch.points = [
            point
            for point in self.sketch.points
            if point.id in used or (point.fixed and point.id not in point_ids)
        ]
        deleted_refs = {
            *(f"entity:{value}" for value in entity_ids),
            *(f"point:{value}" for value in point_ids),
        }
        self.sketch.constraints = [
            constraint
            for constraint in self.sketch.constraints
            if not deleted_refs.intersection(constraint.refs)
        ]
        self._selected_entities.clear()
        self._selected_points.clear()
        self._changed()

    def add_constraint(
        self,
        kind: str,
        refs: tuple[str, ...] | None = None,
        value: float | None = None,
        *,
        name: str = "",
    ) -> bool:
        refs = tuple(refs or self.selected_refs())
        if not refs:
            self.status_message.emit("Select sketch geometry first")
            return False
        before = deepcopy(self.sketch)
        self.sketch.constraints.append(
            SketchConstraint(kind=str(kind), refs=refs, value=value, name=name)
        )
        result = solve_sketch(self.sketch)
        if not result.success:
            self.sketch = before
            self.status_message.emit(result.message)
            self._rebuild_scene(solve=False)
            self.solver_changed.emit(result)
            return False
        self._history.append(before)
        self._future.clear()
        self._last_solve = result
        self._rebuild_scene(solve=False)
        self.solver_changed.emit(result)
        self.sketch_changed.emit()
        return True

    def finish_current_tool(self) -> bool:
        if self.tool == "Spline" and len(self._spline_points) >= 2:
            self._push_history()
            point_ids = tuple(
                self._materialize_point(point, existing)
                for point, existing in self._spline_points
            )
            self.sketch.entities.append(
                SketchSpline(
                    points=point_ids,
                    construction=self.construction,
                )
            )
            self.cancel_tool()
            self._changed()
            return True
        if self.tool == "Polyline" and self._tool_points:
            self.cancel_tool()
            return True
        return False

    def cancel_tool(self) -> None:
        self._tool_points.clear()
        self._spline_points.clear()
        self._rubber_point = None
        self.viewport().update()

    def fit_sketch(self) -> None:
        bounds = self.sketch.bounds()
        if bounds is None:
            self.setSceneRect(QRectF(-100.0, -100.0, 200.0, 200.0))
            self.resetTransform()
            self.scale(4.0, 4.0)
            return
        xmin, ymin, xmax, ymax = bounds
        width = max(float(xmax - xmin), 20.0)
        height = max(float(ymax - ymin), 20.0)
        margin = max(width, height) * 0.25
        rect = QRectF(
            xmin - margin,
            -(ymax + margin),
            width + 2.0 * margin,
            height + 2.0 * margin,
        )
        self.setSceneRect(rect)
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    # ------------------------------------------------------------- interaction
    def wheelEvent(self, event):
        delta = int(event.angleDelta().y())
        if not delta and not event.pixelDelta().isNull():
            delta = int(event.pixelDelta().y() * 8)
        factor = 1.15 ** (float(delta) / 120.0)
        current = abs(float(self.transform().m11()))
        target = current * factor
        if 0.02 <= target <= 5000.0:
            self.scale(factor, factor)
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            if not self.finish_current_tool():
                self.cancel_tool()
            event.accept()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)

        point = self._event_model_point(event)
        if self.tool == "Select":
            self._select_press(event, point)
            return
        snapped, existing = self._snap(point)
        self._draw_click(snapped, existing)
        event.accept()

    def mouseMoveEvent(self, event):
        if self._panning:
            current = event.position().toPoint()
            delta = current - self._pan_start
            self._pan_start = current
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
            return

        model = self._event_model_point(event)
        if self._drag_point_id:
            point = self.sketch.point(self._drag_point_id)
            if not point.fixed:
                snapped, _ = self._snap(model, exclude_point=self._drag_point_id)
                point.x = float(snapped.x())
                point.y = float(snapped.y())
                result = solve_sketch(self.sketch)
                if result.success:
                    self._drag_last_valid = deepcopy(self.sketch)
                    self._last_solve = result
                else:
                    if self._drag_last_valid is not None:
                        self.sketch = deepcopy(self._drag_last_valid)
                    self.status_message.emit(
                        "Constraint prevents moving the point to that position"
                    )
                    self._last_solve = solve_sketch(self.sketch)
                    result = self._last_solve
                self._rebuild_scene(solve=False)
                self._selected_points.add(self._drag_point_id)
                self._sync_selection_style()
                self.solver_changed.emit(result)
            event.accept()
            return

        if self.tool != "Select":
            self._rubber_point = self._snap(model)[0]
            self.viewport().update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton and self._panning:
            self._panning = False
            self.unsetCursor()
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton and self._drag_point_id:
            self._drag_point_id = None
            self._drag_last_valid = None
            self._changed(solve=True)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_tool()
            self.set_tool("Select")
            event.accept()
            return
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            if self.finish_current_tool():
                event.accept()
                return
        if event.key() in {Qt.Key.Key_Delete, Qt.Key.Key_Backspace}:
            self.delete_selected()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Undo):
            self.undo()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Redo):
            self.redo()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.SelectAll):
            self.select_all()
            event.accept()
            return
        super().keyPressEvent(event)

    def _select_press(self, event, model_point: QPointF) -> None:
        additive = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        point_id = self._nearest_point_id(model_point, 9.0)
        if point_id is not None:
            if not additive:
                self._selected_entities.clear()
                self._selected_points.clear()
            if additive and point_id in self._selected_points:
                self._selected_points.remove(point_id)
            else:
                self._selected_points.add(point_id)
                point = self.sketch.point(point_id)
                if not point.fixed:
                    self._push_history()
                    self._drag_point_id = point_id
                    self._drag_last_valid = deepcopy(self.sketch)
            self._sync_selection_style()
            self.selection_changed.emit(self.selected_refs())
            event.accept()
            return

        entity_id = self._entity_at(event.position().toPoint())
        if not additive:
            self._selected_entities.clear()
            self._selected_points.clear()
        if entity_id:
            if additive and entity_id in self._selected_entities:
                self._selected_entities.remove(entity_id)
            else:
                self._selected_entities.add(entity_id)
        self._sync_selection_style()
        self.selection_changed.emit(self.selected_refs())
        event.accept()

    # --------------------------------------------------------------- tool input
    def _draw_click(self, point: QPointF, existing: str | None) -> None:
        if self.tool == "Point":
            self._push_history()
            self._materialize_point(point, existing)
            self._changed()
            return
        if self.tool in {"Line", "Polyline"}:
            self._line_click(point, existing)
            return
        if self.tool == "Rectangle":
            self._two_click(point, existing, self._create_rectangle)
            return
        if self.tool == "Circle":
            self._two_click(point, existing, self._create_circle)
            return
        if self.tool == "Center Arc":
            self._three_click(point, existing, self._create_center_arc)
            return
        if self.tool == "3-Point Arc":
            self._three_click(point, existing, self._create_three_point_arc)
            return
        if self.tool == "Ellipse":
            self._three_click(point, existing, self._create_ellipse)
            return
        if self.tool == "Slot":
            self._three_click(point, existing, self._create_slot)
            return
        if self.tool == "Spline":
            self._spline_points.append((point, existing))
            self._rubber_point = point
            self.viewport().update()

    def _line_click(self, point: QPointF, existing: str | None) -> None:
        if not self._tool_points:
            self._tool_points = [(point, existing)]
            return
        start, start_existing = self._tool_points[-1]
        if _distance(start, point) <= _EPS:
            return
        self._push_history()
        start_id = self._materialize_point(start, start_existing)
        end_id = self._materialize_point(point, existing)
        line = SketchLine(
            start=start_id,
            end=end_id,
            construction=self.construction,
        )
        self.sketch.entities.append(line)
        self._auto_line_constraint(line)
        self._changed()
        if self.tool == "Polyline":
            self._tool_points = [(point, end_id)]
        else:
            self.cancel_tool()

    def _two_click(self, point, existing, callback) -> None:
        self._tool_points.append((point, existing))
        if len(self._tool_points) < 2:
            return
        self._push_history()
        callback(*self._tool_points[:2])
        self.cancel_tool()
        self._changed()

    def _three_click(self, point, existing, callback) -> None:
        self._tool_points.append((point, existing))
        if len(self._tool_points) < 3:
            return
        self._push_history()
        if callback(*self._tool_points[:3]) is False:
            if self._history:
                self._history.pop()
            self.cancel_tool()
            return
        self.cancel_tool()
        self._changed()

    def _create_rectangle(self, first, second) -> None:
        (a, a_existing), (c, c_existing) = first, second
        b = QPointF(c.x(), a.y())
        d = QPointF(a.x(), c.y())
        ids = (
            self._materialize_point(a, a_existing),
            self._materialize_point(b, None),
            self._materialize_point(c, c_existing),
            self._materialize_point(d, None),
        )
        lines = [
            SketchLine(start=ids[0], end=ids[1], construction=self.construction),
            SketchLine(start=ids[1], end=ids[2], construction=self.construction),
            SketchLine(start=ids[2], end=ids[3], construction=self.construction),
            SketchLine(start=ids[3], end=ids[0], construction=self.construction),
        ]
        self.sketch.entities.extend(lines)
        if self.auto_constraints:
            kinds = ("Horizontal", "Vertical", "Horizontal", "Vertical")
            self.sketch.constraints.extend(
                SketchConstraint(kind=kind, refs=(f"entity:{line.id}",))
                for line, kind in zip(lines, kinds)
            )

    def _create_circle(self, first, second) -> None:
        (center, center_existing), (edge, _) = first, second
        center_id = self._materialize_point(center, center_existing)
        self.sketch.entities.append(
            SketchCircle(
                center=center_id,
                radius=max(_distance(center, edge), _EPS),
                construction=self.construction,
            )
        )

    def _create_center_arc(self, first, second, third) -> None:
        (center, center_existing), (start, start_existing), (end, end_existing) = (
            first,
            second,
            third,
        )
        if _distance(center, start) <= _EPS:
            self.status_message.emit("Arc radius must be non-zero")
            return False
        center_id = self._materialize_point(center, center_existing)
        start_id = self._materialize_point(start, start_existing)
        end_id = self._materialize_point(end, end_existing)
        cross = (start.x() - center.x()) * (end.y() - center.y()) - (
            start.y() - center.y()
        ) * (end.x() - center.x())
        self.sketch.entities.append(
            SketchArc(
                center=center_id,
                start=start_id,
                end=end_id,
                clockwise=cross < 0.0,
                construction=self.construction,
            )
        )
        return True

    def _create_three_point_arc(self, first, second, third) -> bool:
        (start, start_existing), (middle, _), (end, end_existing) = first, second, third
        center = _circumcenter(start, middle, end)
        if center is None:
            self.status_message.emit("Three arc points must not be collinear")
            return False
        center_id = self._materialize_point(center, None)
        start_id = self._materialize_point(start, start_existing)
        end_id = self._materialize_point(end, end_existing)
        cross = (middle.x() - start.x()) * (end.y() - middle.y()) - (
            middle.y() - start.y()
        ) * (end.x() - middle.x())
        self.sketch.entities.append(
            SketchArc(
                center=center_id,
                start=start_id,
                end=end_id,
                clockwise=cross < 0.0,
                construction=self.construction,
            )
        )
        return True

    def _create_ellipse(self, first, second, third) -> bool:
        (center, center_existing), (major, major_existing), (minor_point, _) = (
            first,
            second,
            third,
        )
        dx = major.x() - center.x()
        dy = major.y() - center.y()
        major_radius = hypot(dx, dy)
        if major_radius <= _EPS:
            self.status_message.emit("Ellipse major radius must be non-zero")
            return False
        minor_radius = abs(
            (minor_point.x() - center.x()) * (-dy)
            + (minor_point.y() - center.y()) * dx
        ) / major_radius
        if minor_radius <= _EPS:
            self.status_message.emit("Ellipse minor radius must be non-zero")
            return False
        if minor_radius > major_radius + _EPS:
            self.status_message.emit(
                "Ellipse minor radius cannot exceed the major radius; "
                "choose a longer major axis first"
            )
            return False
        center_id = self._materialize_point(center, center_existing)
        major_id = self._materialize_point(major, major_existing)
        self.sketch.entities.append(
            SketchEllipse(
                center=center_id,
                major=major_id,
                minor_radius=minor_radius,
                construction=self.construction,
            )
        )
        return True

    def _create_slot(self, first, second, third) -> bool:
        (a, a_existing), (b, b_existing), (width_point, _) = first, second, third
        dx = b.x() - a.x()
        dy = b.y() - a.y()
        length = hypot(dx, dy)
        if length <= _EPS:
            self.status_message.emit("Slot centerline must have non-zero length")
            return False
        nx, ny = -dy / length, dx / length
        half = abs(
            (width_point.x() - a.x()) * nx
            + (width_point.y() - a.y()) * ny
        )
        if half <= _EPS:
            self.status_message.emit("Slot width must be non-zero")
            return False
        a1 = QPointF(a.x() + nx * half, a.y() + ny * half)
        a2 = QPointF(a.x() - nx * half, a.y() - ny * half)
        b1 = QPointF(b.x() + nx * half, b.y() + ny * half)
        b2 = QPointF(b.x() - nx * half, b.y() - ny * half)
        ids = [self._materialize_point(value, None) for value in (a1, b1, b2, a2)]
        center_a = self._materialize_point(a, a_existing, construction=True)
        center_b = self._materialize_point(b, b_existing, construction=True)
        line1 = SketchLine(start=ids[0], end=ids[1], construction=self.construction)
        line2 = SketchLine(start=ids[2], end=ids[3], construction=self.construction)
        arc_b = SketchArc(
            center=center_b,
            start=ids[1],
            end=ids[2],
            clockwise=True,
            construction=self.construction,
        )
        arc_a = SketchArc(
            center=center_a,
            start=ids[3],
            end=ids[0],
            clockwise=True,
            construction=self.construction,
        )
        self.sketch.entities.extend((line1, arc_b, line2, arc_a))
        if self.auto_constraints:
            self.sketch.constraints.append(
                SketchConstraint(
                    kind="Parallel",
                    refs=(f"entity:{line1.id}", f"entity:{line2.id}"),
                )
            )
        return True

    def _auto_line_constraint(self, line: SketchLine) -> None:
        if not self.auto_constraints:
            return
        point_map = self.sketch.point_map()
        a = point_map[line.start]
        b = point_map[line.end]
        angle = abs(atan2(b.y - a.y, b.x - a.x))
        threshold = 3.0 * pi / 180.0
        if min(angle, abs(pi - angle)) < threshold:
            kind = "Horizontal"
        elif abs(angle - pi / 2.0) < threshold:
            kind = "Vertical"
        else:
            return
        self.sketch.constraints.append(
            SketchConstraint(kind=kind, refs=(f"entity:{line.id}",))
        )

    # --------------------------------------------------------------- rendering
    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        painter.fillRect(rect, _theme("viewport", "#232a32"))
        minor, major = self._grid_spacing()
        if self.show_grid:
            self._draw_grid(painter, rect, minor, major)
        self._draw_axes(painter, rect, major)

    def drawForeground(self, painter: QPainter, _rect: QRectF) -> None:
        if self._rubber_point is None:
            return
        painter.save()
        pen = QPen(_theme("accent", "#3296e6"))
        pen.setCosmetic(True)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        current = self._to_scene(self._rubber_point)
        source = self._spline_points if self.tool == "Spline" else self._tool_points
        if source:
            path = QPainterPath(self._to_scene(source[0][0]))
            for point, _ in source[1:]:
                path.lineTo(self._to_scene(point))
            path.lineTo(current)
            painter.drawPath(path)
        painter.restore()

    def _draw_grid(self, painter: QPainter, rect: QRectF, minor: float, major: float) -> None:
        painter.save()
        minor_color = _theme("border", "#303741")
        minor_color.setAlpha(65)
        major_color = _theme("border_light", "#3a424d")
        major_color.setAlpha(115)
        minor_pen = QPen(minor_color)
        major_pen = QPen(major_color)
        minor_pen.setCosmetic(True)
        major_pen.setCosmetic(True)
        every = max(1, int(round(major / minor)))
        for index in range(int(rect.left() // minor) - 1, int(rect.right() // minor) + 2):
            painter.setPen(major_pen if index % every == 0 else minor_pen)
            x = index * minor
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
        for index in range(int(rect.top() // minor) - 1, int(rect.bottom() // minor) + 2):
            painter.setPen(major_pen if index % every == 0 else minor_pen)
            y = index * minor
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
        painter.restore()

    def _draw_axes(self, painter: QPainter, rect: QRectF, major: float) -> None:
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

        scale = max(abs(float(self.transform().m11())), _EPS)
        offset = 4.0 / scale
        text_pen = QPen(_theme("muted", "#98a2ad"))
        text_pen.setCosmetic(True)
        painter.setPen(text_pen)
        font = QFont(painter.font())
        font.setPointSizeF(8.0)
        painter.setFont(font)
        for index in range(int(rect.left() // major) - 1, int(rect.right() // major) + 2):
            if index:
                value = index * major
                painter.drawText(QPointF(value + offset, -offset), f"{value:g}")
        model_min_y = -rect.bottom()
        model_max_y = -rect.top()
        for index in range(int(model_min_y // major) - 1, int(model_max_y // major) + 2):
            if index:
                value = index * major
                painter.drawText(QPointF(offset, -value - offset), f"{value:g}")
        if self.show_revolve_axis:
            painter.setPen(x_pen)
            painter.drawText(
                QPointF(rect.left() + 12.0 / scale, -8.0 / scale),
                "REVOLVE AXIS  X",
            )
        painter.restore()

    def _rebuild_scene(self, *, solve: bool) -> None:
        if solve:
            self._last_solve = solve_sketch(self.sketch)
            self.solver_changed.emit(self._last_solve)
        self._scene.clear()
        entity_map = self.sketch.entity_map()
        for entity in self.sketch.entities:
            path = self._entity_path(entity)
            if path is None:
                continue
            item = QGraphicsPathItem(path)
            item.setData(_ENTITY_ROLE, str(getattr(entity, "id", "")))
            item.setData(_KIND_ROLE, "entity")
            item.setPen(
                self._construction_pen()
                if getattr(entity, "construction", False)
                else self._normal_pen()
            )
            item.setZValue(2.0)
            self._scene.addItem(item)

        if self.show_points:
            radius = self._pixels_to_scene(3.5)
            for point in self.sketch.points:
                center = self._to_scene(QPointF(point.x, point.y))
                item = QGraphicsEllipseItem(
                    center.x() - radius,
                    center.y() - radius,
                    2.0 * radius,
                    2.0 * radius,
                )
                item.setData(_ENTITY_ROLE, point.id)
                item.setData(_KIND_ROLE, "point")
                pen = QPen(_theme("muted", "#98a2ad"))
                pen.setCosmetic(True)
                item.setPen(pen)
                item.setBrush(_theme("panel_active", "#252b32"))
                item.setZValue(5.0)
                self._scene.addItem(item)

        if self.show_dimensions:
            self._draw_constraint_labels(entity_map)
        self._sync_selection_style()
        self.viewport().update()

    def _entity_path(self, entity):
        points = self.sketch.point_map()
        path = QPainterPath()
        if isinstance(entity, SketchLine):
            a = points.get(entity.start)
            b = points.get(entity.end)
            if a is None or b is None:
                return None
            path.moveTo(a.x, -a.y)
            path.lineTo(b.x, -b.y)
            return path
        if isinstance(entity, SketchCircle):
            center = points.get(entity.center)
            if center is None:
                return None
            radius = abs(float(entity.radius))
            path.addEllipse(QPointF(center.x, -center.y), radius, radius)
            return path
        if isinstance(entity, SketchArc):
            center = points.get(entity.center)
            start = points.get(entity.start)
            end = points.get(entity.end)
            if center is None or start is None or end is None:
                return None
            radius = hypot(start.x - center.x, start.y - center.y)
            if radius <= _EPS:
                return None
            a0 = atan2(start.y - center.y, start.x - center.x)
            a1 = atan2(end.y - center.y, end.x - center.x)
            if entity.clockwise:
                while a1 >= a0:
                    a1 -= 2.0 * pi
            else:
                while a1 <= a0:
                    a1 += 2.0 * pi
            samples = [
                QPointF(
                    center.x + radius * cos(a0 + (a1 - a0) * index / 48.0),
                    center.y + radius * sin(a0 + (a1 - a0) * index / 48.0),
                )
                for index in range(49)
            ]
            path.moveTo(self._to_scene(samples[0]))
            for sample in samples[1:]:
                path.lineTo(self._to_scene(sample))
            return path
        if isinstance(entity, SketchEllipse):
            center = points.get(entity.center)
            major = points.get(entity.major)
            if center is None or major is None:
                return None
            major_radius = hypot(major.x - center.x, major.y - center.y)
            minor_radius = abs(float(entity.minor_radius))
            angle = atan2(major.y - center.y, major.x - center.x)
            ca, sa = cos(angle), sin(angle)
            samples = []
            for index in range(65):
                t = 2.0 * pi * index / 64.0
                x = major_radius * cos(t)
                y = minor_radius * sin(t)
                samples.append(
                    QPointF(
                        center.x + ca * x - sa * y,
                        center.y + sa * x + ca * y,
                    )
                )
            path.moveTo(self._to_scene(samples[0]))
            for sample in samples[1:]:
                path.lineTo(self._to_scene(sample))
            return path
        if isinstance(entity, SketchSpline):
            controls = [points.get(point_id) for point_id in entity.points]
            controls = [point for point in controls if point is not None]
            if len(controls) < 2:
                return None
            samples = _catmull_rom(
                [(point.x, point.y) for point in controls],
                bool(entity.closed),
            )
            path.moveTo(self._to_scene(QPointF(*samples[0])))
            for sample in samples[1:]:
                path.lineTo(self._to_scene(QPointF(*sample)))
            return path
        return None

    def _draw_constraint_labels(self, entity_map) -> None:
        for constraint in self.sketch.constraints:
            anchor = self._constraint_anchor(constraint, entity_map)
            if anchor is None:
                continue
            item = QGraphicsSimpleTextItem(constraint_label(constraint))
            item.setBrush(_theme("accent", "#3296e6"))
            font = QFont()
            font.setPointSizeF(8.0)
            item.setFont(font)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
            item.setPos(
                anchor
                + QPointF(
                    self._pixels_to_scene(5.0),
                    -self._pixels_to_scene(5.0),
                )
            )
            item.setZValue(10.0)
            self._scene.addItem(item)

    def _constraint_anchor(self, constraint, entity_map):
        if not constraint.refs:
            return None
        raw = str(constraint.refs[0])
        if raw.startswith("point:"):
            point = self.sketch.point_map().get(raw.split(":", 1)[1])
            return self._to_scene(QPointF(point.x, point.y)) if point else None
        entity_id = raw.removeprefix("entity:").split(":", 1)[0]
        entity = entity_map.get(entity_id)
        point_map = self.sketch.point_map()
        values = [point_map.get(point_id) for point_id in _entity_point_ids(entity)]
        values = [point for point in values if point is not None]
        if not values:
            return None
        return self._to_scene(
            QPointF(
                sum(point.x for point in values) / len(values),
                sum(point.y for point in values) / len(values),
            )
        )

    def _normal_pen(self) -> QPen:
        fully = bool(self._last_solve and self._last_solve.fully_constrained)
        color = _theme("success", "#49b675") if fully else _theme("text", "#e5e9ef")
        pen = QPen(color)
        pen.setCosmetic(True)
        pen.setWidthF(1.4)
        return pen

    def _selected_pen(self) -> QPen:
        pen = QPen(_theme("accent", "#3296e6"))
        pen.setCosmetic(True)
        pen.setWidthF(2.1)
        return pen

    def _construction_pen(self) -> QPen:
        pen = QPen(_theme("muted", "#98a2ad"))
        pen.setCosmetic(True)
        pen.setWidthF(1.1)
        pen.setStyle(Qt.PenStyle.DashLine)
        return pen

    def _sync_selection_style(self) -> None:
        entity_map = self.sketch.entity_map()
        for item in self._scene.items():
            kind = item.data(_KIND_ROLE)
            object_id = str(item.data(_ENTITY_ROLE) or "")
            if kind == "entity" and isinstance(item, QGraphicsPathItem):
                if object_id in self._selected_entities:
                    item.setPen(self._selected_pen())
                else:
                    entity = entity_map.get(object_id)
                    item.setPen(
                        self._construction_pen()
                        if entity is not None and getattr(entity, "construction", False)
                        else self._normal_pen()
                    )
            elif kind == "point" and isinstance(item, QGraphicsEllipseItem):
                item.setBrush(
                    _theme("accent", "#3296e6")
                    if object_id in self._selected_points
                    else _theme("panel_active", "#252b32")
                )

    # --------------------------------------------------------------- geometry
    def _changed(self, *, solve: bool = True, history_already_pushed: bool = False) -> None:
        del history_already_pushed
        if solve:
            self._last_solve = solve_sketch(self.sketch)
            self.solver_changed.emit(self._last_solve)
        self._rebuild_scene(solve=False)
        self.sketch_changed.emit()

    def _materialize_point(
        self,
        point: QPointF,
        existing: str | None,
        *,
        construction: bool | None = None,
    ) -> str:
        if existing and existing in self.sketch.point_map():
            return existing
        model = SketchPoint(
            x=float(point.x()),
            y=float(point.y()),
            construction=(
                self.construction if construction is None else bool(construction)
            ),
        )
        self.sketch.points.append(model)
        return model.id

    def _snap(self, point: QPointF, exclude_point: str | None = None):
        tolerance = 9.0 / max(abs(float(self.transform().m11())), _EPS)
        if self.sketch.snap_geometry:
            nearest = None
            nearest_distance = float("inf")
            for candidate in self.sketch.points:
                if candidate.id == exclude_point:
                    continue
                distance = hypot(candidate.x - point.x(), candidate.y - point.y())
                if distance <= tolerance and distance < nearest_distance:
                    nearest = candidate
                    nearest_distance = distance
            if nearest is not None:
                return QPointF(nearest.x, nearest.y), nearest.id
        if self.sketch.snap_grid:
            spacing, _ = self._grid_spacing()
            snapped = QPointF(
                round(point.x() / spacing) * spacing,
                round(point.y() / spacing) * spacing,
            )
            if _distance(point, snapped) <= tolerance:
                return snapped, None
        return point, None

    def _nearest_point_id(self, point: QPointF, pixels: float) -> str | None:
        tolerance = float(pixels) / max(abs(float(self.transform().m11())), _EPS)
        result = None
        best = float("inf")
        for candidate in self.sketch.points:
            distance = hypot(candidate.x - point.x(), candidate.y - point.y())
            if distance <= tolerance and distance < best:
                result = candidate.id
                best = distance
        return result

    def _entity_at(self, viewport_point: QPoint) -> str | None:
        scene_point = self.mapToScene(viewport_point)
        radius = self._pixels_to_scene(7.0)
        rect = QRectF(
            scene_point.x() - radius,
            scene_point.y() - radius,
            2.0 * radius,
            2.0 * radius,
        )
        for item in self._scene.items(rect):
            if item.data(_KIND_ROLE) == "entity":
                return str(item.data(_ENTITY_ROLE))
        return None

    def _grid_spacing(self) -> tuple[float, float]:
        scale = max(abs(float(self.transform().m11())), _EPS)
        target = 28.0 / scale
        exponent = 10.0 ** int(log10(max(target, _EPS)))
        normalized = target / exponent
        if normalized < 2.0:
            minor = exponent
        elif normalized < 5.0:
            minor = 2.0 * exponent
        else:
            minor = 5.0 * exponent
        return float(minor), float(minor * 5.0)

    def _pixels_to_scene(self, pixels: float) -> float:
        return float(pixels) / max(abs(float(self.transform().m11())), _EPS)

    def _event_model_point(self, event) -> QPointF:
        scene = self.mapToScene(event.position().toPoint())
        return QPointF(scene.x(), -scene.y())

    @staticmethod
    def _to_scene(point: QPointF) -> QPointF:
        return QPointF(float(point.x()), -float(point.y()))

    @staticmethod
    def _tool_hint(tool: str) -> str:
        return {
            "Select": "Select or drag geometry; hold Shift to extend selection",
            "Point": "Click to place a point",
            "Line": "Click start and end point",
            "Polyline": "Click consecutive vertices; Enter/right-click finishes",
            "Rectangle": "Click two opposite corners",
            "Circle": "Click center and radius point",
            "Center Arc": "Click center, start and end point",
            "3-Point Arc": "Click start, point on arc and end point",
            "Ellipse": "Click center, major-axis point and minor-radius point",
            "Spline": "Click interpolation points; Enter/right-click finishes",
            "Slot": "Click centerline start/end and then a width point",
        }.get(tool, tool)


def _entity_point_ids(entity) -> tuple[str, ...]:
    if isinstance(entity, SketchLine):
        return entity.start, entity.end
    if isinstance(entity, SketchCircle):
        return (entity.center,)
    if isinstance(entity, SketchArc):
        return entity.center, entity.start, entity.end
    if isinstance(entity, SketchEllipse):
        return entity.center, entity.major
    if isinstance(entity, SketchSpline):
        return tuple(entity.points)
    return ()


def _circumcenter(a: QPointF, b: QPointF, c: QPointF) -> QPointF | None:
    ax, ay = float(a.x()), float(a.y())
    bx, by = float(b.x()), float(b.y())
    cx, cy = float(c.x()), float(c.y())
    denominator = 2.0 * (
        ax * (by - cy) + bx * (cy - ay) + cx * (ay - by)
    )
    if abs(denominator) <= _EPS:
        return None
    a2 = ax * ax + ay * ay
    b2 = bx * bx + by * by
    c2 = cx * cx + cy * cy
    return QPointF(
        (a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)) / denominator,
        (a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)) / denominator,
    )


def _catmull_rom(
    points: list[tuple[float, float]],
    closed: bool,
    subdivisions: int = 12,
) -> list[tuple[float, float]]:
    if len(points) < 2:
        return list(points)
    values = list(points)
    if closed:
        padded = [values[-1], *values, values[0], values[1]]
        segments = len(values)
    else:
        padded = [values[0], *values, values[-1]]
        segments = len(values) - 1
    result: list[tuple[float, float]] = []
    for index in range(segments):
        p0, p1, p2, p3 = padded[index : index + 4]
        for step in range(subdivisions):
            t = step / subdivisions
            t2 = t * t
            t3 = t2 * t
            x = 0.5 * (
                2.0 * p1[0]
                + (-p0[0] + p2[0]) * t
                + (2.0 * p0[0] - 5.0 * p1[0] + 4.0 * p2[0] - p3[0]) * t2
                + (-p0[0] + 3.0 * p1[0] - 3.0 * p2[0] + p3[0]) * t3
            )
            y = 0.5 * (
                2.0 * p1[1]
                + (-p0[1] + p2[1]) * t
                + (2.0 * p0[1] - 5.0 * p1[1] + 4.0 * p2[1] - p3[1]) * t2
                + (-p0[1] + 3.0 * p1[1] - 3.0 * p2[1] + p3[1]) * t3
            )
            result.append((x, y))
    result.append(values[0] if closed else values[-1])
    return result
