from __future__ import annotations

import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QMessageBox, QVBoxLayout

from opencae.model.naming import is_unique
from opencae.ui.core.widgets import ChevronComboBox, XYZPicker

_POINT_KINDS = ("geometry_vertex", "datum_point", "reference_point")
_DIRECTION_KINDS = ("geometry_edge", "geometry_face", "datum_vector", "datum_plane")


class CoordinateSystemDialog(QDialog):
    apply_requested = pyqtSignal(object)
    pick_requested = pyqtSignal(object, object, object)
    cancel_pick_requested = pyqtSignal()

    def __init__(self, default_name="CSYS-1", existing_names=(), parent=None):
        super().__init__(parent)
        self.existing_names = tuple(existing_names)
        self.setWindowTitle("Create Coordinate System")
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumWidth(700)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)
        title = QLabel(self.windowTitle())
        title.setObjectName("PanelTitle")
        root.addWidget(title)
        self.form = QFormLayout()
        self.form.setHorizontalSpacing(16)
        self.form.setVerticalSpacing(9)
        self.name = QLineEdit(default_name)
        self.kind = ChevronComboBox()
        self.kind.addItems(("Rectangular", "Cylindrical"))
        self.origin = XYZPicker(allowed=_POINT_KINDS, value_kind="point")
        self.axis_1 = XYZPicker((1.0, 0.0, 0.0), allowed=_DIRECTION_KINDS, value_kind="direction")
        self.axis_2 = XYZPicker((0.0, 1.0, 0.0), allowed=_DIRECTION_KINDS, value_kind="direction")
        for widget in (self.origin, self.axis_1, self.axis_2):
            widget.pick_requested.connect(self.pick_requested)
            widget.cancel_requested.connect(self.cancel_pick_requested)
        self.form.addRow("Name", self.name)
        self.form.addRow("Type", self.kind)
        self.form.addRow("Origin", self.origin)
        self.axis_1_label = QLabel("X direction")
        self.axis_2_label = QLabel("Y direction")
        self.form.addRow(self.axis_1_label, self.axis_1)
        self.form.addRow(self.axis_2_label, self.axis_2)
        root.addLayout(self.form)
        self.kind.currentTextChanged.connect(self._update_labels)

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

    def _update_labels(self, kind):
        cylindrical = str(kind).lower().startswith("cyl")
        self.axis_1_label.setText("Z direction" if cylindrical else "X direction")
        self.axis_2_label.setText("R direction" if cylindrical else "Y direction")

    def values(self):
        return {
            "name": self.name.text().strip(),
            "system_type": self.kind.currentText(),
            "origin": self.origin.value(),
            "axis_1": self.axis_1.value(),
            "axis_2": self.axis_2.value(),
        }

    def _commit(self, close_after):
        values = self.values()
        if not values["name"]:
            QMessageBox.warning(self, "Missing name", "Enter a coordinate system name.")
            return
        if not is_unique(values["name"], self.existing_names):
            QMessageBox.warning(self, "Duplicate name", f"A coordinate system named '{values['name']}' already exists.")
            return
        first = np.asarray(values["axis_1"], dtype=float)
        second = np.asarray(values["axis_2"], dtype=float)
        if np.linalg.norm(first) <= 1.0e-12 or np.linalg.norm(second) <= 1.0e-12:
            QMessageBox.warning(self, "Invalid axes", "Axis directions must be non-zero.")
            return
        if np.linalg.norm(np.cross(first, second)) <= 1.0e-10 * np.linalg.norm(first) * np.linalg.norm(second):
            QMessageBox.warning(self, "Invalid axes", "The two axis directions must not be parallel.")
            return
        self.apply_requested.emit(values)
        if close_after:
            self.accept()

    def closeEvent(self, event):
        for widget in (self.origin, self.axis_1, self.axis_2):
            widget.finish_pick()
        self.cancel_pick_requested.emit()
        super().closeEvent(event)
