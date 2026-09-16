"""Provide selection, display, projection, beam, and fit controls above the viewport."""

from __future__ import annotations

from PyQt6.QtCore import QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QWidget

from opencae.ui.primitives.buttons import ButtonViewportToggle
from opencae.ui.primitives.separators import SeparatorVertical
from opencae.ui.templates import ViewportToolButton


class SelectionToolbar(QWidget):
    """Collect compact viewport mode controls without owning scene state."""

    mode_changed = pyqtSignal(str)
    fit_requested = pyqtSignal()
    display_changed = pyqtSignal(str)
    projection_changed = pyqtSignal(bool)
    beam_physical_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ViewportToolbar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._parallel_projection = False
        self._results_mode = False

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

        self.selection_display_separator = SeparatorVertical(self)
        layout.addWidget(self.selection_display_separator)

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
        self.beam_physical_button = ButtonViewportToggle(
            "Beams",
            tooltip="Render beam profiles as physical solids",
            parent=self,
        )
        self.beam_physical_button.setEnabled(False)
        self.beam_physical_button.toggled.connect(self.beam_physical_changed)
        layout.addWidget(self.beam_physical_button)

        self.beam_view_separator = SeparatorVertical(self)
        layout.addWidget(self.beam_view_separator)

        self.projection_button = self._button("Perspective")
        self.projection_button.setToolTip("Toggle perspective / parallel projection")
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
        """Hide model-edit controls while keeping shared view controls available."""
        self._results_mode = bool(enabled)
        for button in self.mode_buttons.values():
            button.setVisible(not enabled)
        for button in self.display_buttons.values():
            button.setVisible(not enabled)
        self.selection_display_separator.setVisible(not enabled)
        self.beam_physical_button.setVisible(True)
        self.beam_view_separator.setVisible(True)

    def set_beam_available(self, available: bool) -> None:
        """Enable the physical-beam toggle whenever the active context supports it."""
        self.beam_physical_button.setEnabled(bool(available))

    def set_beam_physical(self, enabled: bool) -> None:
        """Synchronize the Beam toggle without re-emitting its request."""
        blocker = QSignalBlocker(self.beam_physical_button)
        self.beam_physical_button.setChecked(bool(enabled))
        del blocker

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

    def _button(self, text, checkable=False):
        """Create every legacy viewport control through the canonical facade."""
        return ViewportToolButton(text, checkable=checkable, parent=self)
