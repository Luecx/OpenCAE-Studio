from PyQt6.QtWidgets import QFormLayout,QLabel,QLineEdit,QMessageBox,QPlainTextEdit,QSpinBox,QTabWidget,QVBoxLayout,QWidget

from opencae.model.core import EntityRef
from opencae.model.entities.fields import FieldDefinition
from opencae.ui.core.apply_dialog import ApplyDialog
from opencae.ui.core.controls import dialog_buttons
from opencae.ui.core.file_path import FilePathEditor
from opencae.ui.core.widgets import ChevronComboBox,ReferenceSelector
from .field_table import FieldTable


class FieldDefinitionDialog(ApplyDialog):
    def __init__(self,field=None,existing_names=(),regions=(),parent=None,default_name="Field-1"):
        super().__init__(parent); self.original=field; self.field=field or FieldDefinition(name=default_name); self.existing=set(existing_names); self.setWindowTitle("Edit Field" if field else "Create Field"); self.setMinimumSize(760,590)
        root=QVBoxLayout(self); root.setContentsMargins(18,16,18,14); title=QLabel(self.windowTitle()); title.setObjectName("PanelTitle"); root.addWidget(title); form=QFormLayout(); self.name=QLineEdit(self.field.name)
        self.location=ChevronComboBox(); self.location.addItems(("Element","Nodal","Element-Nodal")); self.location.setCurrentText(self.field.location); self.components=QSpinBox(); self.components.setRange(1,64); self.components.setValue(self.field.components)
        self.region=ReferenceSelector((("All",None),*regions),self.field.region_ref.entity_id if self.field.region_ref else None); form.addRow("Name",self.name); form.addRow("Location",self.location); form.addRow("Columns",self.components); form.addRow("Region",self.region); root.addLayout(form)
        self.tabs=QTabWidget(); self.table=FieldTable(self.field.components,self.field.table); self.tabs.addTab(self.table,"Tabular"); formula_page=QWidget(); formula_layout=QVBoxLayout(formula_page); self.formula=QPlainTextEdit(self.field.expression); self.formula.setPlaceholderText("Examples: x + y; 2*z; sqrt(x*x+y*y)"); formula_layout.addWidget(self.formula); self.tabs.addTab(formula_page,"Formula")
        file_page=QWidget(); file_form=QFormLayout(file_page); self.file=FilePathEditor(self.field.file_path,"Data files (*.csv *.txt *.dat);;All files (*.*)"); self.interpolation=ChevronComboBox(); self.interpolation.addItems(("Nearest","Linear","Cubic")); self.interpolation.setCurrentText(self.field.interpolation); file_form.addRow("File",self.file); file_form.addRow("Interpolation",self.interpolation); self.tabs.addTab(file_page,"File"); root.addWidget(self.tabs,1); self.components.valueChanged.connect(self.table.set_components); self.tabs.setCurrentIndex({"Tabular":0,"Formula":1,"File":2}.get(self.field.source_type,1)); buttons=dialog_buttons(include_apply=True); self.bind_buttons(buttons,True); root.addWidget(buttons)

    def validate(self):
        name=self.name.text().strip(); duplicates={value.casefold() for value in self.existing}; original=self.original.name.casefold() if self.original else ""
        if not name:QMessageBox.warning(self,"Invalid field","Enter a field name.");return False
        if name.casefold() in duplicates and name.casefold()!=original:QMessageBox.warning(self,"Duplicate name",f"A field named '{name}' already exists.");return False
        return True

    def values(self):
        count=self.components.value(); region_id=self.region.currentValue()
        return dict(name=self.name.text().strip(),location=self.location.currentText(),components=count,component_names=[f"C{i+1}" for i in range(count)],region_ref=EntityRef(str(region_id),"Region") if region_id else None,source_type=("Tabular","Formula","File")[self.tabs.currentIndex()],expression=self.formula.toPlainText().strip(),table=self.table.values(),file_path=self.file.text(),interpolation=self.interpolation.currentText(),field_type="Scalar" if count==1 else "Custom")

    def prepare_new(self, default_name, existing_names):
        self.original = None
        self.existing = set(existing_names)
        self.name.setText(default_name)
