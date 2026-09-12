"""Interactive 2D drafting canvas for persistent OpenCAE sketches."""

from __future__ import annotations

from copy import deepcopy
from math import atan2, cos, hypot, log10, pi, sin

from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
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


def _color(name: str, fallback: str) -> QColor:
    return QColor(str(PALETTE.get(name, fallback)))


class SketchCanvas(QGraphicsView):
    """Precise 2D sketch editor with snapping, constraints and CAD-style tools."""

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
        self._tool_points: list[tuple[QPointF, str | None]] = []
        self._spline_points: list[tuple[QPointF, str | None]] = []
        self._rubber_point: QPointF | None = None
        self._panning = False
        self._pan_start = QPoint()
        self._drag_point_id: str | None = None
        self._drag_before: tuple[float, float] | None = None
        self._selected_entities: set[str] = set()
        self._selected_points: set[str] = set()
        self._history: list[SketchDefinition] = []
        self._future: list[SketchDefinition] = []
        self._last_solve = None
        self._status = ""
        self._rebuild_scene(solve=True)
        self.fit_sketch()

    # ------------------------------------------------------------------ public
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

    def selected_entity_ids(self) -> tuple[str, ...]:
        return tuple(self._selected_entities)

    def selected_point_ids(self) -> tuple[str, ...]:
        return tuple(self._selected_points)

    def selected_refs(self) -> tuple[str, ...]:
        point_refs = tuple(f"point:{value}" for value in self._selected_points)
        entity_refs = tuple(f"entity:{value}" for value in self._selected_entities)
        return point_refs + entity_refs

    def clear_selection(self) -> None:
        self._selected_entities.clear()
        self._selected_points.clear()
        self._sync_selection_style()
        self.selection_changed.emit(())

    def select_all(self) -> None:
        self._selected_entities = {
            str(getattr(entity, "id", "")) for entity in self.sketch.entities
        }
        self._selected_entities.discard("")
        self._selected_points = {point.id for point in self.sketch.points}
        self._sync_selection_style()
        self.selection_changed.emit(self.selected_refs())

    def cancel_tool(self) -> None:
        self._tool_points.clear()
        self._spline_points.clear()
        self._rubber_point = None
        self.viewport().update()

    def finish_current_tool(self) -> bool:
        if self.tool == "Spline" and len(self._spline_points) >= 2:
            self._push_history()
            ids = [self._materialize_point(point, existing) for point, existing in self._spline_points]
            self.sketch.entities.append(
                SketchSpline(points=tuple(ids), construction=self.construction)
            )
            self._spline_points.clear()
            self._rubber_point = None
            self._changed()
            return True
        if self.tool == "Polyline" and self._tool_points:
            self.cancel_tool()
            return True
        return False

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
        self._push_history()
        self.sketch.constraints.append(
            SketchConstraint(kind=str(kind), refs=refs, value=value, name=name)
        )
        result = solve_sketch(self.sketch)
        if not result.success:
            self.sketch = self._history.pop()
            self._future.clear()
            self._rebuild_scene(solve=False)
            self.status_message.emit(result.message)
            return False
        self._changed(solve=False)
        return True

    def remove_selected_constraints(self) -> int:
        selected = set(self.selected_refs())
        if not selected:
            return 0
        before = len(self.sketch.constraints)
        kept = [
            constraint
            for constraint in self.sketch.constraints
            if not selected.intersection(constraint.refs)
        ]
        removed = before - len(kept)
        if removed:
            self._push_history()
            self.sketch.constraints = kept
            self._changed()
        return removed

    def delete_selected(self) -> None:
        entity_ids = set(self._selected_entities)
        point_ids = set(self._selected_points)
        if not entity_ids and not point_ids:
            return
        self._push_history()
        entities = []
        for entity in self.sketch.entities:
            entity_id = str(getattr(entity, "id", ""))
            refs = set(_entity_point_ids(entity))
            if entity_id in entity_ids or refs.intersection(point_ids):
                entity_ids.add(entity_id)
                point_ids.update(refs)
                continue
            entities.append(entity)
        self.sketch.entities = entities
        used = {point_id for entity in entities for point_id in _entity_point_ids(entity)}
        self.sketch.points = [
            point for point in self.sketch.points
            if point.id in used or (point.id not in point_ids and point.fixed)
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
        self.clear_selection()
        self._changed()

    def undo(self) -> None:
        if not self._history:
            return
        self._future.append(deepcopy(self.sketch))
        self.sketch = self._history.pop()
        self.clear_selection()
        self.cancel_tool()
        self._rebuild_scene(solve=True)
        self.sketch_changed.emit()

    def redo(self) -> None:
        if not self._future:
            return
        self._history.append(deepcopy(self.sketch))
        self.sketch = self._future.pop()
        self.clear_selection()
        self.cancel_tool()
        self._rebuild_scene(solve=True)
        self.sketch_changed.emit()

    def fit_sketch(self) -> None:
        bounds = self.sketch.bounds()
        if bounds is None:
            self.setSceneRect(QRectF(-100.0, -100.0, 200.0, 200.0))
            self.resetTransform()
            self.scale(4.0, 4.0)
            return
        xmin, ymin, xmax, ymax = bounds
        width = max(xmax - xmin, 20.0)
        height = max(ymax - ymin, 20.0)
        margin = max(width, height) * 0.2
        rect = QRectF(
            xmin - margin,
            -(ymax + margin),
            width + 2.0 * margin,
            height + 2.0 * margin,
        )
        self.setSceneRect(rect)
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def snapshot(self) -> SketchDefinition:
        return deepcopy(self.sketch)

    # ------------------------------------------------------------- interaction
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if not delta and not event.pixelDelta().isNull():
            delta = event.pixelDelta().y() * 8
        factor = 1.15 ** (float(delta) / 120.0)
        current = self.transform().m11()
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

        model_point = self._event_model_point(event)
        if self.tool == "Select":
            point_id = self._nearest_point_id(model_point, pixels=9.0)
            if point_id is not None:
                additive = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                if not additive:
                    self.clear_selection()
                self._selected_points.add(point_id)
                self._sync_selection_style()
                self.selection_changed.emit(self.selected_refs())
                self._drag_point_id = point_id
                point = self.sketch.point(point_id)
                self._drag_before = (point.x, point.y)
                self._push_history()
                event.accept()
                return
            entity_id = self._entity_at(event.position().toPoint())
            additive = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            if not additive:
                self.clear_selection()
            if entity_id:
                if additive and entity_id in self._selected_entities:
                    self._selected_entities.remove(entity_id)
                else:
                    self._selected_entities.add(entity_id)
                self._sync_selection_style()
                self.selection_changed.emit(self.selected_refs())
            event.accept()
            return

        snapped, existing = self._snap(model_point)
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
        model_point = self._event_model_point(event)
        if self._drag_point_id:
            snapped, _ = self._snap(model_point, exclude_point=self._drag_point_id)
            point = self.sketch.point(self._drag_point_id)
            if not point.fixed:
                point.x, point.y = float(snapped.x()), float(snapped.y())
                solve_sketch(self.sketch)
                self._rebuild_scene(solve=False)
                self._selected_points.add(self._drag_point_id)
                self._sync_selection_style()
            event.accept()
            return
        if self.tool != "Select":
            self._rubber_point = self._snap(model_point)[0]
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
            self._drag_before = None
            self._changed(solve=True, history_already_pushed=True)
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
        if event.matches(event.StandardKey.Undo):
            self.undo()
            event.accept()
            return
        if event.matches(event.StandardKey.Redo):
            self.redo()
            event.accept()
            return
        if event.matches(event.StandardKey.SelectAll):
            self.select_all()
            event.accept()
            return
        super().keyPressEvent(event)

    # --------------------------------------------------------------- rendering
    def drawBackground(self, painter: QPainter, rect: QRectF):
        painter.fillRect(rect, _color("viewport", PALETTE.get("window", "#20242a")))
        if not self.show_grid:
            self._draw_axes(painter, rect, self._major_spacing())
            return
        minor, major = self._grid_spacing()
        self._draw_grid(painter, rect, minor, major)
        self._draw_axes(painter, rect, major)

    def drawForeground(self, painter: QPainter, rect: QRectF):
        if not self._rubber_point:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(_color("accent", "#4da3ff"))
        pen.setCosmetic(True)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        p = QPointF(self._rubber_point.x(), -self._rubber_point.y())
        if self.tool in {"Line", "Polyline", "Rectangle", "Circle", "Ellipse", "Slot"} and self._tool_points:
            a = self._to_scene(self._tool_points[-1][0])
            painter.drawLine(a, p)
        elif self.tool in {"Center Arc", "3-Point Arc"} and self._tool_points:
            for point, _ in self._tool_points:
                painter.drawLine(self._to_scene(point), p)
        elif self.tool == "Spline" and self._spline_points:
            path = QPainterPath(self._to_scene(self._spline_points[0][0]))
            for point, _ in self._spline_points[1:]:
                path.lineTo(self._to_scene(point))
            path.lineTo(p)
            painter.drawPath(path)
        painter.restore()

    def _rebuild_scene(self, *, solve: bool) -> None:
        if solve:
            self._last_solve = solve_sketch(self.sketch)
            self.solver_changed.emit(self._last_solve)
        self._scene.clear()
        entity_pen = self._entity_pen(False)
        construction_pen = self._construction_pen()
        for entity in self.sketch.entities:
            path = self._entity_path(entity)
            if path is None:
                continue
            item = QGraphicsPathItem(path)
            item.setData(_ENTITY_ROLE, str(getattr(entity, "id", "")))
            item.setData(_KIND_ROLE, "entity")
            item.setPen(construction_pen if getattr(entity, "construction", False) else entity_pen)
            item.setZValue(2.0)
            self._scene.addItem(item)
        if self.show_points:
            radius = self._pixels_to_scene(3.5)
            for point in self.sketch.points:
                center = self._to_scene(QPointF(point.x, point.y))
                item = QGraphicsEllipseItem(
                    center.x() - radius,
                    center.y() - radius,
                    radius * 2.0,
                    radius * 2.0,
                )
                item.setData(_ENTITY_ROLE, point.id)
                item.setData(_KIND_ROLE, "point")
                item.setPen(QPen(_color("muted", "#9aa4af"), 0.0))
                item.setBrush(_color("panel_active", "#6b7785"))
                item.setZValue(5.0)
                self._scene.addItem(item)
        if self.show_dimensions:
            self._draw_constraint_labels()
        self._sync_selection_style()
        bounds = self.sketch.bounds()
        if bounds:
            xmin, ymin, xmax, ymax = bounds
            pad = max(xmax - xmin, ymax - ymin, 50.0)
            self._scene.setSceneRect(
                min(self._scene.sceneRect().left(), xmin - pad),
                min(self._scene.sceneRect().top(), -(ymax + pad)),
                max(self._scene.sceneRect().width(), (xmax - xmin) + 2 * pad),
                max(self._scene.sceneRect().height(), (ymax - ymin) + 2 * pad),
            )
        self.viewport().update()

    def _entity_path(self, entity):
        points = self.sketch.point_map()
        path = QPainterPath()
        if isinstance(entity, SketchLine):
            a = points.get(entity.start)
            b = points.get(entity.end)
            if not a or not b:
                return None
            path.moveTo(a.x, -a.y)
            path.lineTo(b.x, -b.y)
            return path
        if isinstance(entity, SketchCircle):
            center = points.get(entity.center)
            if not center:
                return None
            r = abs(float(entity.radius))
            path.addEllipse(QPointF(center.x, -center.y), r, r)
            return path
        if isinstance(entity, SketchArc):
            center = points.get(entity.center)
            start = points.get(entity.start)
            end = points.get(entity.end)
            if not center or not start or not end:
                return None
            radius = hypot(start.x - center.x, start.y - center.y)
            if radius <= _EPS:
                return None
            a0 = atan2(start.y - center.y, start.x - center.x)
            a1 = atan2(end.y - center.y, end.x - center.x)
            if entity.clockwise:
                while a1 >= a0:
                    a1 -= 2 * pi
            else:
                while a1 <= a0:
                    a1 += 2 * pi
            samples = [
                QPointF(
                    center.x + radius * cos(a0 + (a1 - a0) * i / 48.0),
                    center.y + radius * sin(a0 + (a1 - a0) * i / 48.0),
                )
                for i in range(49)
            ]
            path.moveTo(self._to_scene(samples[0]))
            for sample in samples[1:]:
                path.lineTo(self._to_scene(sample))
            return path
        if isinstance(entity, SketchEllipse):
            center = points.get(entity.center)
            major = points.get(entity.major)
            if not center or not major:
                return None
            a = hypot(major.x - center.x, major.y - center.y)
            b = abs(float(entity.minor_radius))
            angle = atan2(major.y - center.y, major.x - center.x)
            samples = []
            ca, sa = cos(angle), sin(angle)
            for i in range(65):
                t = 2 * pi * i / 64.0
                x = a * cos(t)
                y = b * sin(t)
                samples.append(
                    QPointF(center.x + ca * x - sa * y, center.y + sa * x + ca * y)
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
            samples = _catmull_rom([(point.x, point.y) for point in controls], entity.closed)
            path.moveTo(self._to_scene(QPointF(*samples[0])))
            for sample in samples[1:]:
                path.lineTo(self._to_scene(QPointF(*sample)))
            return path
        return None

    def _draw_constraint_labels(self) -> None:
        for constraint in self.sketch.constraints:
            anchor = self._constraint_anchor(constraint)
            if anchor is None:
                continue
            item = QGraphicsSimpleTextItem(constraint_label(constraint))
            item.setBrush(_color("accent", "#4da3ff"))
            font = QFont()
            font.setPointSizeF(8.0)
            item.setFont(font)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
            item.setPos(anchor + QPointF(self._pixels_to_scene(5), -self._pixels_to_scene(5)))
            item.setZValue(10.0)
            self._scene.addItem(item)

    def _constraint_anchor(self, constraint: SketchConstraint) -> QPointF | None:
        refs = constraint.refs
        if not refs:
            return None
        points = self.sketch.point_map()
        entities = self.sketch.entity_map()
        raw = str(refs[0])
        if raw.startswith("point:"):
            point = points.get(raw.split(":", 1)[1])
            return self._to_scene(QPointF(point.x, point.y)) if point else None
        entity_id = raw.removeprefix("entity:").split(":", 1)[0]
        entity = entities.get(entity_id)
        ids = _entity_point_ids(entity) if entity else ()
        values = [points.get(point_id) for point_id in ids]
        values = [point for point in values if point]
        if values:
            x = sum(point.x for point in values) / len(values)
            y = sum(point.y for point in values) / len(values)
            return self._to_scene(QPointF(x, y))
        return None

    def _draw_grid(self, painter: QPainter, rect: QRectF, minor: float, major: float) -> None:
        painter.save()
        minor_pen = QPen(_color("border", "#343a42"))
        minor_pen.setCosmetic(True)
        minor_color = minor_pen.color()
        minor_color.setAlpha(65)
        minor_pen.setColor(minor_color)
        major_pen = QPen(_color("border_light", "#46505b"))
        major_pen.setCosmetic(True)
        major_color = major_pen.color()
        major_color.setAlpha(115)
        major_pen.setColor(major_color)
        left = int(rect.left() // minor) - 1
        right = int(rect.right() // minor) + 1
        top = int(rect.top() // minor) - 1
        bottom = int(rect.bottom() // minor) + 1
        major_every = max(1, int(round(major / minor)))
        for index in range(left, right + 1):
            x = index * minor
            painter.setPen(major_pen if index % major_every == 0 else minor_pen)
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
        for index in range(top, bottom + 1):
            y = index * minor
            painter.setPen(major_pen if index % major_every == 0 else minor_pen)
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
        painter.restore()

    def _draw_axes(self, painter: QPainter, rect: QRectF, major: float) -> None:
        painter.save()
        x_pen = QPen(_color("accent", "#4da3ff"))
        x_pen.setCosmetic(True)
        x_color = x_pen.color(); x_color.setAlpha(175); x_pen.setColor(x_color)
        y_pen = QPen(_color("success", "#5ebd79"))
        y_pen.setCosmetic(True)
        y_color = y_pen.color(); y_color.setAlpha(165); y_pen.setColor(y_color)
        painter.setPen(x_pen)
        painter.drawLine(QPointF(rect.left(), 0.0), QPointF(rect.right(), 0.0))
        painter.setPen(y_pen)
        painter.drawLine(QPointF(0.0, rect.top()), QPointF(0.0, rect.bottom()))

        # Coordinate labels stay readable because the painter is in scene space;
        # scale the font inversely with zoom and place labels on the axes.
        scale = max(self.transform().m11(), _EPS)
        font = painter.font()
        font.setPointSizeF(max(6.5, min(10.0, 8.0 / scale * max(scale, 1.0))))
        painter.setFont(font)
        text_pen = QPen(_color("muted", "#9aa4af")); text_pen.setCosmetic(True)
        painter.setPen(text_pen)
        start_x = int(rect.left() // major) - 1
        end_x = int(rect.right() // major) + 1
        offset = 4.0 / scale
        for index in range(start_x, end_x + 1):
            if index == 0:
                continue
            x = index * major
            painter.drawText(QPointF(x + offset, -offset), f"{x:g}")
        start_y = int((-rect.bottom()) // major) - 1
        end_y = int((-rect.top()) // major) + 1
        for index in range(start_y, end_y + 1):
            if index == 0:
                continue
            model_y = index * major
            painter.drawText(QPointF(offset, -model_y - offset), f"{model_y:g}")
        painter.restore()

    # ------------------------------------------------------------- draw tools
    def _draw_click(self, point: QPointF, existing: str | None) -> None:
        if self.tool == "Point":
            self._push_history()
            self._materialize_point(point, existing, construction=self.construction)
            self._changed()
            return
        if self.tool in {"Line", "Polyline"}:
            self._line_click(point, existing)
            return
        if self.tool == "Rectangle":
            self._two_click_tool(point, existing, self._create_rectangle)
            return
        if self.tool == "Circle":
            self._two_click_tool(point, existing, self._create_circle)
            return
        if self.tool == "Ellipse":
            self._ellipse_click(point, existing)
            return
        if self.tool == "Center Arc":
            self._three_click_tool(point, existing, self._create_center_arc)
            return
        if self.tool == "3-Point Arc":
            self._three_click_tool(point, existing, self._create_three_point_arc)
            return
        if self.tool == "Slot":
            self._three_click_tool(point, existing, self._create_slot)
            return
        if self.tool == "Spline":
            self._spline_points.append((point, existing))
            self._rubber_point = point
            self.viewport().update()
            return

    def _line_click(self, point, existing):
        if not self._tool_points:
            self._tool_points = [(point, existing)]
            return
        first, first_existing = self._tool_points[-1]
        if _qdistance(first, point) <= _EPS:
            return
        self._push_history()
        p1 = self._materialize_point(first, first_existing, construction=self.construction)
        p2 = self._materialize_point(point, existing, construction=self.construction)
        line = SketchLine(start=p1, end=p2, construction=self.construction)
        self.sketch.entities.append(line)
        self._maybe_add_line_auto_constraint(line)
        self._changed()
        if self.tool == "Polyline":
            self._tool_points = [(point, p2)]
        else:
            self._tool_points.clear()
            self._rubber_point = None

    def _two_click_tool(self, point, existing, callback):
        self._tool_points.append((point, existing))
        if len(self._tool_points) < 2:
            return
        self._push_history()
        callback(*self._tool_points[:2])
        self._tool_points.clear()
        self._rubber_point = None
        self._changed()

    def _three_click_tool(self, point, existing, callback):
        self._tool_points.append((point, existing))
        if len(self._tool_points) < 3:
            return
        self._push_history()
        callback(*self._tool_points[:3])
        self._tool_points.clear()
        self._rubber_point = None
        self._changed()

    def _ellipse_click(self, point, existing):
        self._tool_points.append((point, existing))
        if len(self._tool_points) < 3:
            return
        self._push_history()
        (center, center_existing), (major, major_existing), (minor_point, _) = self._tool_points[:3]
        center_id = self._materialize_point(center, center_existing, construction=self.construction)
        major_id = self._materialize_point(major, major_existing, construction=self.construction)
        cx, cy = center.x(), center.y()
        mx, my = major.x() - cx, major.y() - cy
        major_length = max(hypot(mx, my), _EPS)
        distance = abs((minor_point.x() - cx) * (-my) + (minor_point.y() - cy) * mx) / major_length
        self.sketch.entities.append(
            SketchEllipse(
                center=center_id,
                major=major_id,
                minor_radius=max(distance, _EPS),
                construction=self.construction,
            )
        )
        self._tool_points.clear()
        self._rubber_point = None
        self._changed()

    def _create_rectangle(self, first, second):
        (a, a_existing), (c, c_existing) = first, second
        b = QPointF(c.x(), a.y())
        d = QPointF(a.x(), c.y())
        a_id = self._materialize_point(a, a_existing, construction=self.construction)
        c_id = self._materialize_point(c, c_existing, construction=self.construction)
        b_id = self._materialize_point(b, None, construction=self.construction)
        d_id = self._materialize_point(d, None, construction=self.construction)
        lines = [
            SketchLine(start=a_id, end=b_id, construction=self.construction),
            SketchLine(start=b_id, end=c_id, construction=self.construction),
            SketchLine(start=c_id, end=d_id, construction=self.construction),
            SketchLine(start=d_id, end=a_id, construction=self.construction),
        ]
        self.sketch.entities.extend(lines)
        if self.auto_constraints:
            self.sketch.constraints.extend(
                [
                    SketchConstraint(kind="Horizontal", refs=(f"entity:{lines[0].id}",)),
                    SketchConstraint(kind="Vertical", refs=(f"entity:{lines[1].id}",)),
                    SketchConstraint(kind="Horizontal", refs=(f"entity:{lines[2].id}",)),
                    SketchConstraint(kind="Vertical", refs=(f"entity:{lines[3].id}",)),
                ]
            )

    def _create_circle(self, first, second):
        (center, center_existing), (edge, _) = first, second
        radius = max(_qdistance(center, edge), _EPS)
        center_id = self._materialize_point(center, center_existing, construction=self.construction)
        self.sketch.entities.append(
            SketchCircle(center=center_id, radius=radius, construction=self.construction)
        )

    def _create_center_arc(self, first, second, third):
        (center, center_existing), (start, start_existing), (end, end_existing) = first, second, third
        center_id = self._materialize_point(center, center_existing, construction=self.construction)
        start_id = self._materialize_point(start, start_existing, construction=self.construction)
        end_id = self._materialize_point(end, end_existing, construction=self.construction)
        cross = (start.x() - center.x()) * (end.y() - center.y()) - (start.y() - center.y()) * (end.x() - center.x())
        self.sketch.entities.append(
            SketchArc(
                center=center_id,
                start=start_id,
                end=end_id,
                clockwise=cross < 0.0,
                construction=self.construction,
            )
        )

    def _create_three_point_arc(self, first, second, third):
        (start, start_existing), (middle, _), (end, end_existing) = first, second, third
        center = _circumcenter(start, middle, end)
        if center is None:
            self.status_message.emit("Three arc points must not be collinear")
            return
        center_id = self._materialize_point(center, None, construction=self.construction)
        start_id = self._materialize_point(start, start_existing, construction=self.construction)
        end_id = self._materialize_point(end, end_existing, construction=self.construction)
        cross = (middle.x() - start.x()) * (end.y() - middle.y()) - (middle.y() - start.y()) * (end.x() - middle.x())
        self.sketch.entities.append(
            SketchArc(
                center=center_id,
                start=start_id,
                end=end_id,
                clockwise=cross < 0.0,
                construction=self.construction,
            )
        )

    def _create_slot(self, first, second, third):
        (a, a_existing), (b, b_existing), (width_point, _) = first, second, third
        dx, dy = b.x() - a.x(), b.y() - a.y()
        length = hypot(dx, dy)
        if length <= _EPS:
            self.status_message.emit("Slot centerline must have non-zero length")
            return
        nx, ny = -dy / length, dx / length
        half_width = abs((width_point.x() - a.x()) * nx + (width_point.y() - a.y()) * ny)
        if half_width <= _EPS:
            self.status_message.emit("Slot width must be non-zero")
            return
        a1 = QPointF(a.x() + nx * half_width, a.y() + ny * half_width)
        a2 = QPointF(a.x() - nx * half_width, a.y() - ny * half_width)
        b1 = QPointF(b.x() + nx * half_width, b.y() + ny * half_width)
        b2 = QPointF(b.x() - nx * half_width, b.y() - ny * half_width)
        ids = [self._materialize_point(point, None, construction=self.construction) for point in (a1, b1, b2, a2)]
        ca = self._materialize_point(a, a_existing, construction=True)
        cb = self._materialize_point(b, b_existing, construction=True)
        line1 = SketchLine(start=ids[0], end=ids[1], construction=self.construction)
        line2 = SketchLine(start=ids[2], end=ids[3], construction=self.construction)
        arc_b = SketchArc(center=cb, start=ids[1], end=ids[2], clockwise=True, construction=self.construction)
        arc_a = SketchArc(center=ca, start=ids[3], end=ids[0], clockwise=True, construction=self.construction)
        self.sketch.entities.extend((line1, arc_b, line2, arc_a))
        if self.auto_constraints:
            self.sketch.constraints.append(
                SketchConstraint(kind="Parallel", refs=(f"entity:{line1.id}", f"entity:{line2.id}"))
            )

    def _maybe_add_line_auto_constraint(self, line: SketchLine) -> None:
        if not self.auto_constraints:
            return
        points = self.sketch.point_map()
        a, b = points[line.start], points[line.end]
        dx, dy = b.x - a.x, b.y - a.y
        angle = abs(atan2(dy, dx))
        threshold = 3.0 * pi / 180.0
        if min(angle, abs(pi - angle)) < threshold:
            self.sketch.constraints.append(
                SketchConstraint(kind="Horizontal", refs=(f"entity:{line.id}",))
            )
        elif abs(angle - pi / 2.0) < threshold:
            self.sketch.constraints.append(
                SketchConstraint(kind="Vertical", refs=(f"entity:{line.id}",))
            )

    # --------------------------------------------------------------- helpers
    def _push_history(self) -> None:
        self._history.append(deepcopy(self.sketch))
        if len(self._history) > 100:
            self._history.pop(0)
        self._future.clear()

    def _changed(self, *, solve: bool = True, history_already_pushed: bool = False) -> None:
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
            construction=self.construction if construction is None else bool(construction),
        )
        self.sketch.points.append(model)
        return model.id

    def _snap(self, point: QPointF, exclude_point: str | None = None):
        scale = max(self.transform().m11(), _EPS)
        tolerance = 9.0 / scale
        if self.sketch.snap_geometry:
            best = None
            best_distance = float("inf")
            for candidate in self.sketch.points:
                if candidate.id == exclude_point:
                    continue
                distance = hypot(candidate.x - point.x(), candidate.y - point.y())
                if distance < tolerance and distance < best_distance:
                    best = candidate
                    best_distance = distance
            if best is not None:
                return QPointF(best.x, best.y), best.id
        if self.sketch.snap_grid:
            spacing = self._minor_spacing()
            if spacing > _EPS:
                snapped = QPointF(
                    round(point.x() / spacing) * spacing,
                    round(point.y() / spacing) * spacing,
                )
                if _qdistance(point, snapped) <= tolerance:
                    return snapped, None
        return point, None

    def _nearest_point_id(self, point: QPointF, pixels: float = 8.0):
        scale = max(self.transform().m11(), _EPS)
        tolerance = pixels / scale
        best = None
        best_distance = float("inf")
        for candidate in self.sketch.points:
            distance = hypot(candidate.x - point.x(), candidate.y - point.y())
            if distance <= tolerance and distance < best_distance:
                best = candidate.id
                best_distance = distance
        return best

    def _entity_at(self, viewport_point: QPoint) -> str | None:
        scene_point = self.mapToScene(viewport_point)
        radius = self._pixels_to_scene(7.0)
        rect = QRectF(scene_point.x() - radius, scene_point.y() - radius, radius * 2, radius * 2)
        for item in self._scene.items(rect):
            if item.data(_KIND_ROLE) == "entity":
                return str(item.data(_ENTITY_ROLE))
        return None

    def _sync_selection_style(self) -> None:
        for item in self._scene.items():
            kind = item.data(_KIND_ROLE)
            object_id = str(item.data(_ENTITY_ROLE) or "")
            if kind == "entity" and isinstance(item, QGraphicsPathItem):
                entity = self.sketch.entity_map().get(object_id)
                if object_id in self._selected_entities:
                    item.setPen(self._selected_pen())
                elif entity is not None and getattr(entity, "construction", False):
                    item.setPen(self._construction_pen())
                else:
                    item.setPen(self._entity_pen(False))
            elif kind == "point" and isinstance(item, QGraphicsEllipseItem):
                if object_id in self._selected_points:
                    item.setBrush(_color("accent", "#4da3ff"))
                else:
                    item.setBrush(_color("panel_active", "#6b7785"))

    def _entity_pen(self, selected: bool) -> QPen:
        result = self._last_solve
        fully = bool(result and result.fully_constrained)
        color = _color("accent", "#4da3ff") if selected else (
            _color("success", "#68b77a") if fully else _color("text", "#e5e9ee")
        )
        pen = QPen(color)
        pen.setCosmetic(True)
        pen.setWidthF(2.0 if selected else 1.4)
        return pen

    def _selected_pen(self) -> QPen:
        return self._entity_pen(True)

    def _construction_pen(self) -> QPen:
        pen = QPen(_color("muted", "#8b96a3"))
        pen.setCosmetic(True)
        pen.setWidthF(1.1)
        pen.setStyle(Qt.PenStyle.DashLine)
        return pen

    def _event_model_point(self, event) -> QPointF:
        scene = self.mapToScene(event.position().toPoint())
        return QPointF(scene.x(), -scene.y())

    @staticmethod
    def _to_scene(point: QPointF) -> QPointF:
        return QPointF(float(point.x()), -float(point.y()))

    def _pixels_to_scene(self, pixels: float) -> float:
        return float(pixels) / max(abs(self.transform().m11()), _EPS)

    def _minor_spacing(self) -> float:
        minor, _ = self._grid_spacing()
        return minor

    def _major_spacing(self) -> float:
        _, major = self._grid_spacing()
        return major

    def _grid_spacing(self):
        scale = max(abs(self.transform().m11()), _EPS)
        target_world = 28.0 / scale
        if target_world <= 0.0:
            return 1.0, 10.0
        exponent = 10.0 ** int(log10(target_world))
        normalized = target_world / exponent
        if normalized < 2.0:
            minor = exponent
        elif normalized < 5.0:
            minor = 2.0 * exponent
        else:
            minor = 5.0 * exponent
        return minor, minor * 5.0

    @staticmethod
    def _tool_hint(tool: str) -> str:
        hints = {
            "Select": "Select or drag geometry; Shift adds to selection",
            "Point": "Click to place a point",
            "Line": "Click start and end point",
            "Polyline": "Click consecutive vertices; Enter or right-click finishes",
            "Rectangle": "Click two opposite corners",
            "Circle": "Click center and radius point",
            "Center Arc": "Click center, start and end",
            "3-Point Arc": "Click start, point on arc and end",
            "Ellipse": "Click center, major-axis point and minor-radius point",
            "Spline": "Click control points; Enter or right-click finishes",
            "Slot": "Click centerline start/end and then half-width",
        }
        return hints.get(tool, tool)


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


def _qdistance(a: QPointF, b: QPointF) -> float:
    return hypot(float(a.x() - b.x()), float(a.y() - b.y()))


def _circumcenter(a: QPointF, b: QPointF, c: QPointF) -> QPointF | None:
    ax, ay = a.x(), a.y()
    bx, by = b.x(), b.y()
    cx, cy = c.x(), c.y()
    d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) <= _EPS:
        return None
    a2 = ax * ax + ay * ay
    b2 = bx * bx + by * by
    c2 = cx * cx + cy * cy
    ux = (a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)) / d
    uy = (a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)) / d
    return QPointF(ux, uy)


def _catmull_rom(points: list[tuple[float, float]], closed: bool, subdivisions: int = 12):
    if len(points) < 2:
        return points
    values = list(points)
    if closed:
        padded = [values[-1], *values, values[0], values[1 if len(values) > 1 else 0]]
        segment_count = len(values)
    else:
        padded = [values[0], *values, values[-1]]
        segment_count = len(values) - 1
    result = []
    for index in range(segment_count):
        p0, p1, p2, p3 = padded[index:index + 4]
        for step in range(subdivisions):
            t = step / subdivisions
            t2 = t * t
            t3 = t2 * t
            x = 0.5 * (
                2 * p1[0]
                + (-p0[0] + p2[0]) * t
                + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
            )
            y = 0.5 * (
                2 * p1[1]
                + (-p0[1] + p2[1]) * t
                + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
            )
            result.append((x, y))
    result.append(values[0] if closed else values[-1])
    return result
