from __future__ import annotations

import math

from PyQt6.QtCore import QSignalBlocker, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QToolButton,
    QWidget,
    QWidgetAction,
)

from opencae.ui.core.icon_factory import IconKind
from .result_widgets import ribbon_button


class _Vector3Editor(QWidget):
    changed = pyqtSignal()

    def __init__(self, value=(0.0, 0.0, 0.0), parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.editors: list[QDoubleSpinBox] = []
        for axis, component in zip("XYZ", value, strict=True):
            editor = QDoubleSpinBox()
            editor.setRange(-1.0e30, 1.0e30)
            editor.setDecimals(7)
            editor.setValue(float(component))
            editor.setPrefix(f"{axis}: ")
            editor.setMinimumWidth(92)
            editor.valueChanged.connect(lambda _value: self.changed.emit())
            self.editors.append(editor)
            layout.addWidget(editor, 1)

    def value(self) -> tuple[float, float, float]:
        return tuple(editor.value() for editor in self.editors)

    def set_value(self, value) -> None:
        values = tuple(float(component) for component in value)
        if len(values) != 3:
            raise ValueError("A vector requires exactly three components")
        blockers = [QSignalBlocker(editor) for editor in self.editors]
        for editor, component in zip(self.editors, values, strict=True):
            editor.setValue(component)
        del blockers


class ResultSectionButton(QToolButton):
    """Split ribbon button controlling the interactive result clipping plane."""

    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        template = ribbon_button("Section View", IconKind.SECTION_VIEW, False, 92)
        self.setText(template.text())
        self.setIcon(template.icon())
        self.setIconSize(template.iconSize())
        self.setToolButtonStyle(template.toolButtonStyle())
        self.setProperty("ribbonButton", True)
        self.setFixedSize(92, 70)
        self.setCheckable(True)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)

        self._origin_is_automatic = True
        panel = QWidget()
        form = QFormLayout(panel)
        form.setContentsMargins(12, 10, 12, 10)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)

        self.origin = _Vector3Editor()
        self.normal = _Vector3Editor((1.0, 0.0, 0.0))
        form.addRow("Origin", self.origin)
        form.addRow("Normal", self.normal)

        axes = QWidget()
        axis_layout = QHBoxLayout(axes)
        axis_layout.setContentsMargins(0, 0, 0, 0)
        axis_layout.setSpacing(4)
        for label, vector in (
            ("X", (1.0, 0.0, 0.0)),
            ("Y", (0.0, 1.0, 0.0)),
            ("Z", (0.0, 0.0, 1.0)),
        ):
            button = QPushButton(label)
            button.setFixedWidth(48)
            button.clicked.connect(lambda _checked=False, value=vector: self._set_axis(value))
            axis_layout.addWidget(button)
        axis_layout.addStretch(1)
        form.addRow("Align normal", axes)

        self.invert = QCheckBox("Invert clipping direction")
        self.show_plane = QCheckBox("Show interactive plane")
        self.show_plane.setChecked(True)
        form.addRow("", self.invert)
        form.addRow("", self.show_plane)

        center = QPushButton("Center on current result")
        center.clicked.connect(self._request_center)
        form.addRow("", center)

        menu = QMenu(self)
        action = QWidgetAction(menu)
        action.setDefaultWidget(panel)
        menu.addAction(action)
        self.setMenu(menu)

        self.toggled.connect(self.settings_changed.emit)
        self.origin.changed.connect(self._origin_edited)
        self.normal.changed.connect(self.settings_changed.emit)
        self.invert.toggled.connect(self.settings_changed.emit)
        self.show_plane.toggled.connect(self.settings_changed.emit)

    def values(self) -> dict:
        return {
            "enabled": self.isChecked(),
            "origin": None if self._origin_is_automatic else self.origin.value(),
            "normal": self._normalized(self.normal.value()),
            "invert": self.invert.isChecked(),
            "show_plane": self.show_plane.isChecked(),
        }

    def set_state(self, state: dict | None) -> None:
        """Receive plane updates from the viewport without re-rendering the result."""
        state = state or {}
        blockers = [
            QSignalBlocker(self),
            QSignalBlocker(self.invert),
            QSignalBlocker(self.show_plane),
        ]
        if "enabled" in state:
            self.setChecked(bool(state["enabled"]))
        origin = state.get("origin")
        if origin is not None:
            self.origin.set_value(origin)
            self._origin_is_automatic = False
        normal = state.get("normal")
        if normal is not None:
            self.normal.set_value(self._normalized(normal))
        if "invert" in state:
            self.invert.setChecked(bool(state["invert"]))
        if "show_plane" in state:
            self.show_plane.setChecked(bool(state["show_plane"]))
        del blockers

    def reset_for_result(self) -> None:
        self._origin_is_automatic = True

    def _origin_edited(self) -> None:
        self._origin_is_automatic = False
        self.settings_changed.emit()

    def _request_center(self) -> None:
        self._origin_is_automatic = True
        self.settings_changed.emit()

    def _set_axis(self, value) -> None:
        self.normal.set_value(value)
        self.settings_changed.emit()

    @staticmethod
    def _normalized(value) -> tuple[float, float, float]:
        vector = tuple(float(component) for component in value)
        length = math.sqrt(sum(component * component for component in vector))
        if length <= 1.0e-14:
            return (1.0, 0.0, 0.0)
        return tuple(component / length for component in vector)
