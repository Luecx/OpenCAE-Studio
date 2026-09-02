"""Provide selection, display, projection, and fit controls above the 3D viewport."""

from __future__ import annotations

from PyQt6.QtCore import QSignalBlocker, pyqtSignal
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QToolButton, QWidget


class SelectionToolbar(QWidget):
    """Collect compact viewport mode controls without owning scene state."""

    mode_changed = pyqtSignal(str)
    fit_requested = pyqtSignal()
    display_changed = pyqtSignal(str)
    projection_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ViewportToolbar")
        self._parallel_projection = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(4)

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_buttons = {}
        for index, (text, mode) in enumerate(
            (
                ("Auto", "auto"),
                ("Point", "point"),
                ("Edge", "edge"),
                ("Face", "face"),
                ("Cell", "cell"),
                ("Element", "element"),
            )
        ):
            button = self._button(text, True)
            button.setToolTip("Available while a dialog requests viewport selection")
            self.mode_buttons[mode] = button
            self.mode_group.addButton(button, index)
            layout.addWidget(button)
            button.clicked.connect(
                lambda _checked=False, value=mode: self.mode_changed.emit(value)
            )

        layout.addSpacing(8)
        self.display_buttons = {}
        self.display_group = QButtonGroup(self)
        self.display_group.setExclusive(True)
        for text, mode in (("Geometry", "geometry"), ("Mesh", "mesh")):
            button = self._button(text, True)
            self.display_buttons[mode] = button
            self.display_group.addButton(button)
            layout.addWidget(button)
            button.clicked.connect(
                lambda _checked=False, value=mode: self.display_changed.emit(value)
            )
        self.display_buttons["geometry"].setChecked(True)

        layout.addStretch(1)
        self.projection_button = self._button("Perspective")
        self.projection_button.setObjectName("ProjectionToggle")
        self.projection_button.setToolTip("Toggle perspective / parallel projection")
        # The label changes, not the control geometry.  This avoids the stale
        # checked-border footprint that previously looked like a blue shadow.
        metrics = self.projection_button.fontMetrics()
        width = max(
            metrics.horizontalAdvance("Perspective"),
            metrics.horizontalAdvance("Parallel"),
        ) + 24
        self.projection_button.setFixedWidth(width)
        self.projection_button.clicked.connect(self._projection_clicked)
        layout.addWidget(self.projection_button)

        self.fit_button = self._button("Fit")
        self.fit_button.setToolTip("Center and fit the visible model")
        self.fit_button.clicked.connect(self.fit_requested)
        layout.addWidget(self.fit_button)

        self.set_selection_enabled(False)

    def set_results_mode(self, enabled):
        """Hide topology/display controls that do not apply to stored result views."""
        for button in self.mode_buttons.values():
            button.setVisible(not enabled)
        for button in self.display_buttons.values():
            button.setVisible(not enabled)

    def set_selection_enabled(self, enabled: bool, allowed_modes=None):
        """Enable only the mode buttons owned by the active pick session."""
        allowed = set(self.mode_buttons if allowed_modes is None else allowed_modes)
        for mode, button in self.mode_buttons.items():
            button.setEnabled(bool(enabled) and mode in allowed)
        if not enabled:
            self.set_mode("none")

    def set_mode(self, mode):
        """Synchronize the checked selection-mode button without re-emitting it."""
        button = self.mode_buttons.get(mode)
        if button is not None:
            blocker = QSignalBlocker(button)
            button.setChecked(True)
            del blocker
            return

        self.mode_group.setExclusive(False)
        try:
            for item in self.mode_buttons.values():
                blocker = QSignalBlocker(item)
                item.setChecked(False)
                del blocker
        finally:
            self.mode_group.setExclusive(True)

    def set_display(self, mode):
        """Synchronize the Geometry/Mesh display toggle without re-emitting it."""
        button = self.display_buttons.get(mode)
        if button:
            blocker = QSignalBlocker(button)
            button.setChecked(True)
            del blocker

    def set_projection(self, parallel: bool):
        """Update the fixed-width projection label without a check-state decoration."""
        self._parallel_projection = bool(parallel)
        self.projection_button.setText(
            "Parallel" if self._parallel_projection else "Perspective"
        )

    def _projection_clicked(self, _checked=False):
        requested = not self._parallel_projection
        viewport = self.parentWidget()
        plotter = getattr(viewport, "plotter", None)
        setter = getattr(plotter, "set_parallel_projection", None)
        if setter is None or not setter(requested):
            return
        self.set_projection(requested)
        self.projection_changed.emit(requested)

    @staticmethod
    def _button(text, checkable=False):
        button = QToolButton()
        button.setText(text)
        button.setCheckable(checkable)
        button.setProperty("viewportTool", True)
        return button
