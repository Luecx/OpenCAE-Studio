"""Provides the interactive result section-view ribbon control."""

from __future__ import annotations

import math

from PyQt6.QtCore import QSignalBlocker, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QRadioButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from opencae.ui.core.icon_factory import IconKind
from opencae.ui.templates import (
    PRIMARY_CONTROL_HEIGHT,
    SectionHeading,
    Vector3Input,
    field_block,
)

from .result_widgets import ribbon_button


class ResultSectionButton(QToolButton):
    """Open clipping-plane state and geometry settings from one ribbon popup."""

    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        """Build an instant popup with explicit section-view on/off controls."""
        super().__init__(parent)
        template = ribbon_button("Section View", IconKind.SECTION_VIEW, False, 92)
        self.setText(template.text())
        self.setIcon(template.icon())
        self.setIconSize(template.iconSize())
        self.setToolButtonStyle(template.toolButtonStyle())
        self.setProperty("ribbonButton", True)
        self.setFixedSize(92, 70)
        self.setCheckable(False)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        self._origin_is_automatic = True
        panel = QWidget()
        panel.setMinimumWidth(360)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        layout.addWidget(SectionHeading("Display"))
        state_row = QWidget()
        state_layout = QHBoxLayout(state_row)
        state_layout.setContentsMargins(0, 0, 0, 0)
        state_layout.setSpacing(16)
        self.section_off = QRadioButton("Off")
        self.section_on = QRadioButton("On")
        self.section_off.setChecked(True)
        self.state_group = QButtonGroup(self)
        self.state_group.addButton(self.section_off)
        self.state_group.addButton(self.section_on)
        state_layout.addWidget(self.section_off)
        state_layout.addWidget(self.section_on)
        state_layout.addStretch(1)
        layout.addWidget(field_block("Section view", state_row))

        layout.addWidget(SectionHeading("Plane"))
        self.origin = Vector3Input()
        self.normal = Vector3Input((1.0, 0.0, 0.0))
        layout.addWidget(field_block("Origin", self.origin))
        layout.addWidget(field_block("Normal", self.normal))

        layout.addWidget(SectionHeading("Options"))
        self.invert = QCheckBox("Invert clipping direction")
        self.show_plane = QCheckBox("Show interactive plane")
        self.show_plane.setChecked(True)
        layout.addWidget(self.invert)
        layout.addWidget(self.show_plane)

        center = QPushButton("Center on current result")
        center.setFixedHeight(PRIMARY_CONTROL_HEIGHT)
        center.clicked.connect(self._request_center)
        layout.addWidget(center)

        menu = QMenu(self)
        action = QWidgetAction(menu)
        action.setDefaultWidget(panel)
        menu.addAction(action)
        self.setMenu(menu)

        self.section_on.toggled.connect(self.settings_changed.emit)
        self.origin.changed.connect(self._origin_edited)
        self.normal.changed.connect(self.settings_changed.emit)
        self.invert.toggled.connect(self.settings_changed.emit)
        self.show_plane.toggled.connect(self.settings_changed.emit)

    def values(self) -> dict:
        """Return the clipping-plane state consumed by the result viewport."""
        return {
            "enabled": self.section_on.isChecked(),
            "origin": None if self._origin_is_automatic else self.origin.value(),
            "origin_auto": self._origin_is_automatic,
            "normal": self._normalized(self.normal.value()),
            "invert": self.invert.isChecked(),
            "show_plane": self.show_plane.isChecked(),
        }

    def set_state(self, state: dict | None) -> None:
        """Receive plane updates from the viewport without re-rendering the result."""
        state = state or {}
        blockers = [
            QSignalBlocker(self.section_on),
            QSignalBlocker(self.section_off),
            QSignalBlocker(self.invert),
            QSignalBlocker(self.show_plane),
        ]
        if "enabled" in state:
            (self.section_on if state["enabled"] else self.section_off).setChecked(True)
        origin = state.get("origin")
        if origin is not None:
            # Show the resolved current center numerically, but do not turn an
            # automatically centered plane into a manual plane just because the
            # viewport reported the resolved coordinates back to the ribbon.
            self.origin.set_value(origin)
        if "origin_auto" in state:
            self._origin_is_automatic = bool(state["origin_auto"])
        elif origin is not None:
            # Backward compatibility for state producers predating origin_auto.
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
        """Return the section origin to automatic centering for a newly opened result."""
        self._origin_is_automatic = True

    def _origin_edited(self) -> None:
        """Mark the origin as manually controlled after direct user editing."""
        self._origin_is_automatic = False
        self.settings_changed.emit()

    def _request_center(self) -> None:
        """Ask the viewport to keep the clipping plane centered on the current result."""
        self._origin_is_automatic = True
        self.settings_changed.emit()

    @staticmethod
    def _normalized(value) -> tuple[float, float, float]:
        """Return a safe unit normal, falling back to global X for zero vectors."""
        vector = tuple(float(component) for component in value)
        length = math.sqrt(sum(component * component for component in vector))
        if length <= 1.0e-14:
            return (1.0, 0.0, 0.0)
        return tuple(component / length for component in vector)
