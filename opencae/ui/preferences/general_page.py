"""Provides general application appearance and behavior preferences."""

from __future__ import annotations

from PyQt6.QtWidgets import QCheckBox, QVBoxLayout, QWidget

from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.templates import SectionHeading, apply_primary_control_height, field_block, field_row


class GeneralPage(QWidget):
    """Edit theme, icon sizing, confirmation and layout-restoration preferences."""

    def __init__(self, settings, parent=None):
        """Build general settings using the same label-above hierarchy as dialogs."""
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        root.addWidget(SectionHeading("Appearance"))
        self.theme = _combo(
            ("Dark", "Light", "System"),
            str(settings.value("ui/theme", "Dark")),
        )
        self.icon_scale = _combo(
            ("Compact", "Normal", "Large"),
            str(settings.value("ui/icon_scale", "Normal")),
        )
        root.addWidget(
            field_row(
                field_block("Theme", self.theme),
                field_block("Icon scale", self.icon_scale),
            )
        )

        root.addWidget(SectionHeading("Behavior"))
        self.confirm_delete = QCheckBox("Confirm destructive actions")
        self.confirm_delete.setChecked(
            str(settings.value("ui/confirm_delete", "true")).lower() != "false"
        )
        self.restore_layout = QCheckBox("Restore window layout")
        self.restore_layout.setChecked(
            str(settings.value("ui/restore_layout", "true")).lower() != "false"
        )
        root.addWidget(self.confirm_delete)
        root.addWidget(self.restore_layout)
        root.addStretch(1)

    def values(self):
        """Return the preference values represented by this page."""
        return {
            "theme": self.theme.currentText(),
            "icon_scale": self.icon_scale.currentText(),
            "confirm_delete": self.confirm_delete.isChecked(),
            "restore_layout": self.restore_layout.isChecked(),
        }


def _combo(values, current):
    """Create a canonical preference combo with the requested current value."""
    combo = ChevronComboBox()
    combo.setMinimumWidth(0)
    combo.addItems(values)
    combo.setCurrentText(current)
    apply_primary_control_height(combo)
    return combo
