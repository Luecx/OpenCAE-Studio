from PyQt6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QWidget


class GeneralPage(QWidget):
    def __init__(self, settings, parent=None):
        super().__init__(parent); form = QFormLayout(self)
        self.theme = QComboBox(); self.theme.addItems(("Dark", "Light", "System")); self.theme.setCurrentText(str(settings.value("ui/theme", "Dark")))
        self.icon_scale = QComboBox(); self.icon_scale.addItems(("Compact", "Normal", "Large")); self.icon_scale.setCurrentText(str(settings.value("ui/icon_scale", "Normal")))
        self.confirm_delete = QCheckBox(); self.confirm_delete.setChecked(str(settings.value("ui/confirm_delete", "true")).lower() != "false")
        self.restore_layout = QCheckBox(); self.restore_layout.setChecked(str(settings.value("ui/restore_layout", "true")).lower() != "false")
        form.addRow("Theme", self.theme); form.addRow("Icon scale", self.icon_scale)
        form.addRow("Confirm destructive actions", self.confirm_delete); form.addRow("Restore window layout", self.restore_layout)

    def values(self):
        return {"theme": self.theme.currentText(), "icon_scale": self.icon_scale.currentText(), "confirm_delete": self.confirm_delete.isChecked(), "restore_layout": self.restore_layout.isChecked()}
