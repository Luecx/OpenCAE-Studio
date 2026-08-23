"""Provides the Results ribbon deformation toggle and scale flyout."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QMenu, QToolButton, QVBoxLayout, QWidget, QWidgetAction

from opencae.ui.core.icon_factory import IconKind
from opencae.ui.templates import NumericUnitInput, button, field_block

from .result_widgets import ribbon_button


class ResultDeformationButton(QToolButton):
    """Toggle deformed results and edit their display-only scaling factor."""

    settings_changed = pyqtSignal()
    auto_requested = pyqtSignal()

    def __init__(self, parent=None):
        """Build the ribbon button and a canonical label-above scale flyout."""
        super().__init__(parent)
        template = ribbon_button("Deformed", IconKind.DEFORMATION, False)
        self.setText(template.text())
        self.setIcon(template.icon())
        self.setIconSize(template.iconSize())
        self.setToolButtonStyle(template.toolButtonStyle())
        self.setProperty("ribbonButton", True)
        self.setFixedSize(82, 70)
        self.setCheckable(True)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

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

        self.toggled.connect(self.settings_changed.emit)
        self.scale.valueChanged.connect(self.settings_changed.emit)

    def values(self):
        """Return whether deformation is enabled and its current display scale."""
        return self.isChecked(), self.scale.value()

    def set_scale(self, value):
        """Replace the current deformation scale without changing enable state."""
        self.scale.setValue(float(value))
