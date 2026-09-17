"""Provides the interactive result section-view ribbon control."""

from __future__ import annotations

import math

from PyQt6.QtCore import QSignalBlocker, pyqtSignal
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QVBoxLayout, QWidget

from opencae.ui.components.controls import ControlVector3
from opencae.ui.foundation.icons import IconKind, make_icon
from opencae.ui.foundation.metrics import PRIMARY_CONTROL_HEIGHT
from opencae.ui.primitives.buttons.button_form_action import ButtonFormAction
from opencae.ui.primitives.buttons.button_results_ribbon_options import (
    ButtonResultsRibbonOptions,
)
from opencae.ui.primitives.checks import CheckForm
from opencae.ui.primitives.labels import LabelSection
from opencae.ui.primitives.radios import RadioForm
from opencae.ui.components.form_field import FormField

class ResultSectionButton(ButtonResultsRibbonOptions):
    """Open clipping-plane state and geometry settings from one ribbon popup."""

    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(
            "Section View",
            icon=make_icon(IconKind.SECTION_VIEW, 28),
            width=92,
            parent=parent,
        )

        self._origin_is_automatic = True
        panel = QWidget()
        panel.setMinimumWidth(360)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        layout.addWidget(LabelSection("Display"))
        state_row = QWidget()
        state_layout = QHBoxLayout(state_row)
        state_layout.setContentsMargins(0, 0, 0, 0)
        state_layout.setSpacing(16)
        self.section_off = RadioForm("Off", checked=True)
        self.section_on = RadioForm("On")
        self.state_group = QButtonGroup(self)
        self.state_group.addButton(self.section_off)
        self.state_group.addButton(self.section_on)
        state_layout.addWidget(self.section_off)
        state_layout.addWidget(self.section_on)
        state_layout.addStretch(1)
        layout.addWidget(FormField("Section view", state_row))

        layout.addWidget(LabelSection("Plane"))
        self.origin = ControlVector3()
        self.normal = ControlVector3((1.0, 0.0, 0.0))
        layout.addWidget(FormField("Origin", self.origin))
        layout.addWidget(FormField("Normal", self.normal))

        layout.addWidget(LabelSection("Options"))
        self.invert = CheckForm("Invert clipping direction")
        self.show_plane = CheckForm("Show interactive plane", checked=True)
        layout.addWidget(self.invert)
        layout.addWidget(self.show_plane)

        center = ButtonFormAction("Center on current result", parent=panel)
        center.setFixedHeight(PRIMARY_CONTROL_HEIGHT)
        center.clicked.connect(self._request_center)
        layout.addWidget(center)

        self.set_options_panel(panel)
        self.section_on.toggled.connect(self.settings_changed.emit)
        self.origin.changed.connect(self._origin_edited)
        self.normal.changed.connect(self.settings_changed.emit)
        self.invert.toggled.connect(self.settings_changed.emit)
        self.show_plane.toggled.connect(self.settings_changed.emit)

    def values(self) -> dict:
        return {
            "enabled": self.section_on.isChecked(),
            "origin": None if self._origin_is_automatic else self.origin.value(),
            "origin_auto": self._origin_is_automatic,
            "normal": self._normalized(self.normal.value()),
            "invert": self.invert.isChecked(),
            "show_plane": self.show_plane.isChecked(),
        }

    def set_state(self, state: dict | None) -> None:
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
            self.origin.set_value(origin)
        if "origin_auto" in state:
            self._origin_is_automatic = bool(state["origin_auto"])
        elif origin is not None:
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

    @staticmethod
    def _normalized(value) -> tuple[float, float, float]:
        vector = tuple(float(component) for component in value)
        length = math.sqrt(sum(component * component for component in vector))
        if length <= 1.0e-14:
            return (1.0, 0.0, 0.0)
        return tuple(component / length for component in vector)
