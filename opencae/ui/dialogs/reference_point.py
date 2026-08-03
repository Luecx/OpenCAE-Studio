from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QMessageBox, QVBoxLayout

from opencae.model.naming import is_unique
from opencae.ui.core.widgets import XYZPicker


_POINT_KINDS = ("geometry_vertex", "datum_point", "reference_point")


class ReferencePointDialog(QDialog):
    apply_requested = pyqtSignal(object)
    pick_requested = pyqtSignal(object, object, object)
    cancel_pick_requested = pyqtSignal()

    def __init__(self, default_name="RP-1", existing_names=(), parent=None):
        super().__init__(parent)
        self.existing_names = tuple(existing_names)
        self.setWindowTitle("Create Reference Point")
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumWidth(640)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)
        title = QLabel(self.windowTitle())
        title.setObjectName("PanelTitle")
        root.addWidget(title)
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(9)
        self.name = QLineEdit(default_name)
        self.position = XYZPicker(allowed=_POINT_KINDS, value_kind="point")
        self.position.pick_requested.connect(self.pick_requested)
        self.position.cancel_requested.connect(self.cancel_pick_requested)
        form.addRow("Name", self.name)
        form.addRow("Position", self.position)
        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Close
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName("PrimaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Ok).clicked.connect(lambda: self._commit(True))
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(lambda: self._commit(False))
        buttons.rejected.connect(self.close)
        root.addWidget(buttons)

    def values(self):
        return {"name": self.name.text().strip(), "position": self.position.value()}

    def _commit(self, close_after):
        values = self.values()
        if not values["name"]:
            QMessageBox.warning(self, "Missing name", "Enter a reference point name.")
            return
        if not is_unique(values["name"], self.existing_names):
            QMessageBox.warning(self, "Duplicate name", f"A reference point named '{values['name']}' already exists.")
            return
        self.apply_requested.emit(values)
        if close_after:
            self.accept()

    def closeEvent(self, event):
        self.position.finish_pick()
        self.cancel_pick_requested.emit()
        super().closeEvent(event)
