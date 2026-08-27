"""Provides the Results ribbon deformation settings flyout."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QMenu,
    QRadioButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from opencae.ui.core.icon_factory import IconKind
from opencae.ui.templates import NumericUnitInput, button, field_block

from .result_widgets import ribbon_button


class ResultDeformationButton(QToolButton):
    """Open deformation state and scale settings from one ribbon popup."""

    settings_changed = pyqtSignal()
    auto_requested = pyqtSignal()

    def __init__(self, parent=None):
        """Build an instant popup with explicit on/off radio buttons."""
        super().__init__(parent)
        template = ribbon_button("Deformed", IconKind.DEFORMATION, False)
        self.setText(template.text())
        self.setIcon(template.icon())
        self.setIconSize(template.iconSize())
        self.setToolButtonStyle(template.toolButtonStyle())
        self.setProperty("ribbonButton", True)
        self.setFixedSize(82, 70)
        self.setCheckable(False)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        panel = QWidget()
        panel.setMinimumWidth(300)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        state_row = QWidget()
        state_layout = QHBoxLayout(state_row)
        state_layout.setContentsMargins(0, 0, 0, 0)
        state_layout.setSpacing(16)
        self.disabled = QRadioButton("Off")
        self.enabled = QRadioButton("On")
        self.disabled.setChecked(True)
        self.state_group = QButtonGroup(self)
        self.state_group.addButton(self.disabled)
        self.state_group.addButton(self.enabled)
        state_layout.addWidget(self.disabled)
        state_layout.addWidget(self.enabled)
        state_layout.addStretch(1)
        layout.addWidget(field_block("Deformation", state_row))

        self.scale = NumericUnitInput(
            1.0,
            "",
            minimum=0.0,
            maximum=1e12,
            decimals=6,
        )
        layout.addWidget(field_block("Deformation scaling factor", self.scale))

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(8)
        auto = button("Auto")
        reset = button("Reset to 1")
        auto.clicked.connect(self.auto_requested.emit)
        reset.clicked.connect(lambda: self.scale.setValue(1.0))
        actions.addWidget(auto)
        actions.addWidget(reset)
        layout.addLayout(actions)

        menu = QMenu(self)
        action = QWidgetAction(menu)
        action.setDefaultWidget(panel)
        menu.addAction(action)
        self.setMenu(menu)

        self.enabled.toggled.connect(self.settings_changed.emit)
        self.scale.valueChanged.connect(self.settings_changed.emit)

    def values(self):
        """Return whether deformation is enabled and its current display scale."""
        return self.enabled.isChecked(), self.scale.value()

    def set_scale(self, value):
        """Replace the current deformation scale without changing enable state."""
        self.scale.setValue(float(value))
