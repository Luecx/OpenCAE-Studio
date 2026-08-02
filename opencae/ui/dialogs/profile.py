from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractItemView, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,  QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from opencae.model.entities.profiles.calculations import profile_parameters, profile_properties
from opencae.ui.core.controls import dialog_buttons
from opencae.ui.core.widgets import ChevronComboBox
from .profile_graph_editor import GraphProfileEditor

PROFILE_TYPES = ("Rectangle", "Box", "Pipe", "Circle", "I-profile", "H-profile", "C-profile", "U-profile", "General", "Graph profile")


class ProfileDialog(QDialog):
    def __init__(self, profile=None, existing_names=(), parent=None, initial_type=None, default_name="Profile-1"):
        super().__init__(parent)
        self.profile = profile; self.existing_names = {name.casefold() for name in existing_names}; self._editors = {}
        self.setWindowTitle("Edit Profile" if profile else "Create Profile"); self.setMinimumSize(880, 520)
        root = QVBoxLayout(self); root.setContentsMargins(18,16,18,14); root.setSpacing(12)
        title=QLabel(self.windowTitle()); title.setObjectName("PanelTitle"); root.addWidget(title)
        top=QFormLayout(); self.name=QLineEdit(profile.name if profile else default_name); self.kind=ChevronComboBox(); self.kind.addItems(PROFILE_TYPES); self.kind.setCurrentText(profile.profile_type if profile else (initial_type or "Box"))
        top.addRow("Name",self.name); top.addRow("Profile type",self.kind); root.addLayout(top)
        body=QHBoxLayout(); self.form_host=QWidget(); self.form=QFormLayout(self.form_host); self.form.setVerticalSpacing(9); body.addWidget(self.form_host,1)
        self.properties=QTableWidget(0,3); self.properties.setHorizontalHeaderLabels(("Property","Value","Unit")); self.properties.horizontalHeader().setStretchLastSection(True); self.properties.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); body.addWidget(self.properties,1)
        root.addLayout(body,1)
        buttons=dialog_buttons(); buttons.accepted.connect(self._accept); buttons.rejected.connect(self.reject); root.addWidget(buttons)
        self.kind.currentTextChanged.connect(self._rebuild); self._rebuild()

    def _rebuild(self):
        while self.form.rowCount(): self.form.removeRow(0)
        self._editors={}; current=self.profile.dimensions if self.profile and self.kind.currentText()==self.profile.profile_type else {}
        if self.kind.currentText()=="Graph profile":
            editor=GraphProfileEditor(current.get("nodes","1,-20,0\n2,20,0"),current.get("segments","1,2,2.0")); editor.connect_changed(self._update_properties)
            self._editors["graph"]=editor; self.form.addRow(editor)
        else:
            for key,label,default in profile_parameters(self.kind.currentText()):
                editor=QDoubleSpinBox(); editor.setRange(-1e30,1e30); editor.setDecimals(6); editor.setValue(float(current.get(key,default))); editor.valueChanged.connect(self._update_properties)
                editor.setMinimumWidth(320); self._editors[key]=editor; self.form.addRow(label,editor)
        self._update_properties()

    def _dimensions(self):
        if "graph" in self._editors:return self._editors["graph"].values()
        return {key:editor.value() for key,editor in self._editors.items()}

    def _update_properties(self):
        data=profile_properties(self.kind.currentText(),self._dimensions()); self.properties.setRowCount(len(data))
        units={"Area":"mm²","Centroid y":"mm","Centroid z":"mm","Iyy":"mm⁴","Izz":"mm⁴","Iyz":"mm⁴","Torsion constant":"mm⁴"}
        for row,(name,value) in enumerate(data.items()):
            self.properties.setItem(row,0,QTableWidgetItem(name)); self.properties.setItem(row,1,QTableWidgetItem(f"{value:.8g}")); self.properties.setItem(row,2,QTableWidgetItem(units.get(name,"")))

    def _accept(self):
        name=self.name.text().strip()
        if not name: QMessageBox.warning(self,"Invalid profile","Enter a profile name."); return
        if name.casefold() in self.existing_names and (self.profile is None or name.casefold()!=self.profile.name.casefold()): QMessageBox.warning(self,"Duplicate name",f"A profile named '{name}' already exists."); return
        self.accept()

    def values(self): return {"name":self.name.text().strip(),"profile_type":self.kind.currentText(),"dimensions":self._dimensions()}
