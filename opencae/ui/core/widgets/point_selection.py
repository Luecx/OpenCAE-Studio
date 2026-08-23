"""Provides the compact point-list editor used by partition workflows."""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QListWidget, QVBoxLayout, QWidget

from opencae.ui.templates import PRIMARY_CONTROL_HEIGHT, button


class PointSelectionWidget(QWidget):
    """Capture and display an ordered set of points from the active viewport selection."""

    def __init__(self, points=(), selection_provider=None, parent=None):
        """Build the point list and its capture/clear action row."""
        super().__init__(parent)
        self._provider = selection_provider
        self._points = []

        self.list = QListWidget()
        self.list.setMinimumHeight(82)
        self.set_points(points)

        capture = button("Use current point selection", clicked=self.capture)
        clear = button("Clear", clicked=lambda: self.set_points(()))
        capture.setFixedHeight(PRIMARY_CONTROL_HEIGHT)
        clear.setFixedHeight(PRIMARY_CONTROL_HEIGHT)

        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(capture)
        row.addWidget(clear)
        row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.list)
        layout.addLayout(row)

    def capture(self):
        """Replace the list with the viewport's current point selection."""
        if self._provider is not None:
            self.set_points(self._provider() or ())

    def set_points(self, points):
        """Replace points and refresh their concise coordinate labels."""
        self._points = [tuple(map(float, point)) for point in points]
        self.list.clear()
        for index, point in enumerate(self._points, 1):
            self.list.addItem(
                f"Point {index}: ({point[0]:.6g}, {point[1]:.6g}, {point[2]:.6g})"
            )

    def points(self):
        """Return a copy of the current ordered point coordinates."""
        return list(self._points)
