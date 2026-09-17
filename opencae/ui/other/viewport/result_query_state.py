"""Own drag-safe node and element query state for displayed solver results."""

from __future__ import annotations

import logging

import numpy as np
from PyQt6.QtCore import QEvent, QObject, Qt

from opencae.ui.foundation.theme import PALETTE
from .result_query import element_values, node_values
from .safe_operations import disable_picking, remove_actor

LOGGER = logging.getLogger(__name__)
_QUERY_DRAG_THRESHOLD = 4.0


class _ResultQueryMouseFilter(QObject):
    """Delay VTK left-button rotation until a query gesture becomes a real drag."""

    def __init__(self, state) -> None:
        super().__init__(state.owner.plotter)
        self.state = state
        self._installed = False
        self._press = None
        self._press_modifiers = Qt.KeyboardModifier.NoModifier
        self._drag_started = False

    def set_active(self, active: bool) -> None:
        widget = self.state.owner.plotter
        active = bool(active)
        if active and not self._installed:
            widget.installEventFilter(self)
            self._installed = True
        elif not active and self._installed:
            widget.removeEventFilter(self)
            self._installed = False
        if not active:
            self._cancel_drag()
        self._reset()

    def eventFilter(self, watched, event):
        if not self.state.handles_direct_click():
            return False
        try:
            event_type = event.type()
        except (AttributeError, RuntimeError):
            return False

        if event_type == QEvent.Type.MouseButtonPress:
            if self._button(event) != Qt.MouseButton.LeftButton:
                return False
            self._press = self._position(event)
            self._press_modifiers = self._modifiers(event)
            self._drag_started = False
            event.accept()
            return True

        if event_type == QEvent.Type.MouseMove and self._press is not None:
            if not self._buttons(event) & Qt.MouseButton.LeftButton:
                return False
            current = self._position(event)
            if current is None:
                return True
            if (
                not self._drag_started
                and self._distance_squared(self._press, current)
                > _QUERY_DRAG_THRESHOLD ** 2
            ):
                self._drag_started = self._begin_camera_drag()
            return not self._drag_started

        if event_type != QEvent.Type.MouseButtonRelease:
            return False
        if self._button(event) != Qt.MouseButton.LeftButton or self._press is None:
            return False

        if self._drag_started:
            self._reset()
            return False

        press = self._press
        current = self._position(event)
        self._reset()
        if current is None:
            return True
        if self._distance_squared(press, current) > _QUERY_DRAG_THRESHOLD ** 2:
            return True

        cursor = self.state.owner._event_display_position(watched, event)
        if cursor is not None:
            self.state.pick_display_position(cursor)
        event.accept()
        return True

    def _begin_camera_drag(self) -> bool:
        plotter = self.state.owner.plotter
        if self._press is None:
            return False
        try:
            ctrl = bool(
                self._press_modifiers & Qt.KeyboardModifier.ControlModifier
            )
            shift = bool(
                self._press_modifiers & Qt.KeyboardModifier.ShiftModifier
            )
            plotter._setEventInformation(
                float(self._press[0]),
                float(self._press[1]),
                ctrl,
                shift,
                chr(0),
                0,
                None,
            )
            plotter._active_button = Qt.MouseButton.LeftButton
            plotter._Iren.LeftButtonPressEvent()
            show_pivot = getattr(plotter, "_show_rotation_pivot", None)
            if callable(show_pivot):
                show_pivot()
            return True
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return False

    def _cancel_drag(self) -> None:
        if not self._drag_started:
            return
        plotter = self.state.owner.plotter
        try:
            plotter._Iren.LeftButtonReleaseEvent()
            plotter._active_button = Qt.MouseButton.NoButton
            hide_pivot = getattr(plotter, "_hide_rotation_pivot", None)
            if callable(hide_pivot):
                hide_pivot()
        except (AttributeError, RuntimeError, TypeError, ValueError):
            pass

    def _reset(self) -> None:
        self._press = None
        self._press_modifiers = Qt.KeyboardModifier.NoModifier
        self._drag_started = False

    @staticmethod
    def _button(event):
        try:
            return event.button()
        except (AttributeError, RuntimeError):
            return Qt.MouseButton.NoButton

    @staticmethod
    def _buttons(event):
        try:
            return event.buttons()
        except (AttributeError, RuntimeError):
            return Qt.MouseButton.NoButton

    @staticmethod
    def _modifiers(event):
        try:
            return event.modifiers()
        except (AttributeError, RuntimeError):
            return Qt.KeyboardModifier.NoModifier

    @staticmethod
    def _position(event):
        try:
            point = event.position()
        except (AttributeError, RuntimeError):
            return None
        return float(point.x()), float(point.y())

    @staticmethod
    def _distance_squared(first, second) -> float:
        dx = float(second[0]) - float(first[0])
        dy = float(second[1]) - float(first[1])
        return dx * dx + dy * dy


class ResultQueryState:
    """Resolve result queries while preserving click-versus-camera-drag semantics."""

    def __init__(self, owner):
        self.owner = owner
        self.mode = ""
        self.field = None
        self._marker = "result-query-marker"
        self._edges = "result-query-edges"
        self._mouse_filter = _ResultQueryMouseFilter(self)

    def configure(self, mode, field=None):
        """Enable or disable node/element querying with a pre-rotation drag gate."""
        self.mode, self.field = mode or "", field
        self._remove_marker()
        disable_picking(self.owner.plotter)
        active = self.handles_direct_click()
        self._mouse_filter.set_active(active)
        if not active:
            self.owner.query_panel.clear_query()
            return
        self.owner.query_panel.show_prompt(self.mode)
        self.owner.canvas._position_overlays()

    def handles_direct_click(self) -> bool:
        """Return whether the current Results state should consume an ordinary click."""
        return bool(
            self.mode in {"node", "element"}
            and self.owner.stage == "RESULTS"
            and self.owner.scene.result_grid is not None
            and self.owner.scene.result_actor is not None
        )

    def pick_display_position(self, cursor) -> bool:
        """Resolve one accepted Qt click to a world point on the result actor."""
        if not self.handles_direct_click():
            return False
        try:
            from vtkmodules.vtkRenderingCore import vtkCellPicker

            picker = vtkCellPicker()
            picker.SetTolerance(0.0005)
            picker.PickFromListOn()
            picker.AddPickList(self.owner.scene.result_actor)
            hit = bool(
                picker.Pick(
                    float(cursor[0]),
                    float(cursor[1]),
                    0.0,
                    self.owner.plotter.renderer,
                )
            )
            if not hit:
                return False
            point = tuple(float(value) for value in picker.GetPickPosition())
        except (ImportError, AttributeError, TypeError, ValueError, RuntimeError):
            return False
        self._picked(point)
        return True

    def clear(self):
        """Clear the current result-query marker and overlay text."""
        self._remove_marker()
        self.owner.query_panel.clear_query()

    def _remove_marker(self):
        """Remove transient query marker actors without forcing a render."""
        for name in (self._marker, self._edges):
            remove_actor(self.owner.plotter, name)

    def _picked(self, point):
        """Present node or element values at a picked result-surface position."""
        grid = self.owner.scene.result_grid
        if point is None or grid is None:
            return
        suffix = (
            f" — {self.field.name} / "
            f"{self.field.metadata.get('component', 'Magnitude')}"
            if self.field is not None
            else ""
        )
        if self.mode == "node":
            index, result = node_values(grid, point, self.field)
            marker = grid.points[index]
            title = "Node Query" + suffix
        else:
            index, result = element_values(grid, point, self.field)
            marker = grid.get_cell(index).center
            title = "Element Query" + suffix
            self._highlight_element(grid, index)
        self.owner.plotter.add_points(
            np.asarray([marker]),
            color=PALETTE["query_marker"],
            point_size=14,
            render_points_as_spheres=True,
            name=self._marker,
            pickable=False,
            render=False,
        )
        self.owner.query_panel.show_result(title, result)
        self.owner.canvas._position_overlays()
        self.owner.plotter.render()

    def _highlight_element(self, grid, index):
        """Draw the queried element's edges without disturbing result picking."""
        remove_actor(self.owner.plotter, self._edges)
        try:
            edges = grid.extract_cells([int(index)]).extract_all_edges()
            self.owner.plotter.add_mesh(
                edges,
                color=PALETTE["query_marker"],
                line_width=4.0,
                lighting=False,
                name=self._edges,
                pickable=False,
                render=False,
            )
        except (AttributeError, IndexError, RuntimeError, ValueError):
            return
        except Exception:
            LOGGER.exception(
                "Unexpected failure while highlighting queried element %s",
                index,
            )
