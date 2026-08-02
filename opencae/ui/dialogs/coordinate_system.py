from PyQt6.QtWidgets import QDialog, QDoubleSpinBox, QFormLayout, QLabel, QLineEdit, QMessageBox, QStackedWidget, QVBoxLayout, QWidget

from opencae.model.naming import is_unique
from opencae.ui.core.controls import dialog_buttons
from opencae.ui.core.widgets import ChevronComboBox


def _vector_form(labels, defaults):
    page = QWidget(); form = QFormLayout(page); editors = []
    for label, value in zip(labels, defaults):
        editor = QDoubleSpinBox(); editor.setRange(-1e12, 1e12); editor.setDecimals(6); editor.setValue(value)
        form.addRow(label, editor); editors.append(editor)
    return page, editors


class CoordinateSystemDialog(QDialog):
    def __init__(self, default_name="CSYS-1", existing_names=(), parent=None):
        super().__init__(parent); self.existing_names = tuple(existing_names); self.setWindowTitle("Create Coordinate System"); self.setMinimumWidth(560)
        root = QVBoxLayout(self); root.setContentsMargins(18, 16, 18, 14)
        title = QLabel(self.windowTitle()); title.setObjectName("PanelTitle"); root.addWidget(title)
        form = QFormLayout(); self.name = QLineEdit(default_name); self.kind = ChevronComboBox(); self.kind.addItems(("Rectangular", "Cylindrical"))
        form.addRow("Name", self.name); form.addRow("Type", self.kind); root.addLayout(form)
        self.stack = QStackedWidget(); root.addWidget(self.stack)
        rectangular = (("X direction X", "X direction Y", "X direction Z", "Y direction X", "Y direction Y", "Y direction Z"), (1, 0, 0, 0, 1, 0))
        cylindrical = (("Base X", "Base Y", "Base Z", "Point on Z axis X", "Point on Z axis Y", "Point on Z axis Z", "Point on R axis X", "Point on R axis Y", "Point on R axis Z"), (0, 0, 0, 0, 0, 1, 1, 0, 0))
        page, self.rect = _vector_form(*rectangular); self.stack.addWidget(page)
        page, self.cyl = _vector_form(*cylindrical); self.stack.addWidget(page)
        self.kind.currentIndexChanged.connect(self.stack.setCurrentIndex)
        buttons = dialog_buttons(); buttons.accepted.connect(self._accept); buttons.rejected.connect(self.reject); root.addWidget(buttons)


    def _accept(self):
        name = self.name.text().strip()
        if not is_unique(name, self.existing_names): QMessageBox.warning(self, "Duplicate name", f"A coordinate system named '{name}' already exists."); return
        self.accept()

    def values(self):
        if self.kind.currentText() == "Rectangular":
            v = [item.value() for item in self.rect]
            return {"name": self.name.text().strip(), "system_type": "Rectangular", "origin": (0.0, 0.0, 0.0), "axis_1": tuple(v[:3]), "axis_2": tuple(v[3:])}
        v = [item.value() for item in self.cyl]; base = tuple(v[:3]); z_point = tuple(v[3:6]); r_point = tuple(v[6:9])
        return {"name": self.name.text().strip(), "system_type": "Cylindrical", "origin": base,
                "axis_1": tuple(z_point[i] - base[i] for i in range(3)), "axis_2": tuple(r_point[i] - base[i] for i in range(3))}
