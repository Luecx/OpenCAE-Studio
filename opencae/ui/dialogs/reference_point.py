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

    def __init__(self, default_name="RP-1", existing_names=(), parent=None, units=None):
        super().__init__(parent)
        units = units or getattr(getattr(parent, "controllers", None), "units", None)
        self.existing_names = tuple(existing_names)
        self.setWindowTitle("Create Reference Point")
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumWidth(520)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)
        title = QLabel(self.windowTitle())
        title.setObjectName("PanelTitle")
        root.addWidget(title)

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.name = QLineEdit(default_name)
        self.position = XYZPicker(
            allowed=_POINT_KINDS,
            value_kind="point",
            suffix=units.suffix("length") if units is not None else "",
        )
        self.position.pick_requested.connect(self.pick_requested)
        self.position.cancel_requested.connect(self.cancel_pick_requested)
        self.position.changed.connect(self._preview)
        self.name.textChanged.connect(self._preview)
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
        self.resize(560, self.sizeHint().height())

    def values(self):
        return {"name": self.name.text().strip(), "position": self.position.value()}

    def _viewport(self):
        return getattr(self.parent(), "viewport", None)

    def _preview(self, *_):
        viewport = self._viewport()
        if viewport is None:
            return
        name = self.name.text().strip() or "Reference Point"
        viewport.show_reference_point_preview(name, self.position.value())

    def _clear_preview(self):
        viewport = self._viewport()
        if viewport is not None:
            viewport.clear_reference_point_preview()

    def _commit(self, close_after):
        values = self.values()
        if not values["name"]:
            QMessageBox.warning(self, "Missing name", "Enter a reference point name.")
            return
        if not is_unique(values["name"], self.existing_names):
            QMessageBox.warning(self, "Duplicate name", f"A reference point named '{values['name']}' already exists.")
            return
        self._clear_preview()
        self.apply_requested.emit(values)
        if close_after:
            self.accept()

    def showEvent(self, event):
        super().showEvent(event)
        self._preview()

    def closeEvent(self, event):
        self.position.finish_pick()
        self.cancel_pick_requested.emit()
        self._clear_preview()
        super().closeEvent(event)
