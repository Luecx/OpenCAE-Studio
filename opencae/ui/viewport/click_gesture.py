"""Classify Qt mouse gestures as clicks without consuming camera interaction events."""

from __future__ import annotations

from PyQt6.QtCore import Qt


class ClickGestureTracker:
    """Track one left-button gesture and reject releases that followed a drag."""

    def __init__(self, drag_threshold: float = 4.0):
        """Create a tracker using a small logical-pixel camera-drag threshold."""
        self.drag_threshold = max(0.0, float(drag_threshold))
        self._press = None
        self._dragged = False

    def press(self, event) -> None:
        """Start tracking a left-button gesture from its global Qt position."""
        if self._button(event) != Qt.MouseButton.LeftButton:
            return
        self._press = self._position(event)
        self._dragged = False

    def move(self, event) -> None:
        """Mark the active gesture as a drag once pointer motion is meaningful."""
        if self._press is None:
            return
        try:
            buttons = event.buttons()
        except (AttributeError, RuntimeError):
            return
        if not buttons & Qt.MouseButton.LeftButton:
            return
        current = self._position(event)
        if current is None:
            return
        if self._distance_squared(self._press, current) > self.drag_threshold ** 2:
            self._dragged = True

    def release_is_click(self, event) -> bool:
        """Finish the gesture and return True only for a stationary left click."""
        if self._button(event) != Qt.MouseButton.LeftButton:
            return False
        press = self._press
        current = self._position(event)
        dragged = self._dragged
        self.reset()
        if press is None or current is None:
            return False
        return bool(
            not dragged
            and self._distance_squared(press, current) <= self.drag_threshold ** 2
        )

    def reset(self) -> None:
        """Forget any incomplete gesture, for example when picking is disabled."""
        self._press = None
        self._dragged = False

    @staticmethod
    def _button(event):
        try:
            return event.button()
        except (AttributeError, RuntimeError):
            return Qt.MouseButton.NoButton

    @staticmethod
    def _position(event):
        try:
            point = event.globalPosition()
        except (AttributeError, RuntimeError):
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
