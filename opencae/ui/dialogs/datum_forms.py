from PyQt6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QWidget
from opencae.ui.core.widgets import PickReference


def page(rows):
    widget = QWidget(); form = QFormLayout(widget); form.setHorizontalSpacing(16); form.setVerticalSpacing(9)
    for label, control in rows: form.addRow(label, control)
    return widget

def number(value=0.0, minimum=-1e15, maximum=1e15):
    control = QDoubleSpinBox(); control.setRange(minimum,maximum); control.setDecimals(8); control.setValue(value); return control

def xyz(prefix="", values=(0.0,0.0,0.0)): return {f"{prefix}{axis}":number(value) for axis,value in zip("xyz",values)}
def references(*allowed):
    expanded = []
    for value in allowed:
        group = ("geometry_vertex", "datum_point", "reference_point") if value == "point" else (value,)
        for kind in group:
            if kind not in expanded:
                expanded.append(kind)
    return PickReference(tuple(expanded))
def choice(values):
    control = QComboBox(); control.addItems(values); return control
def check(text="", checked=False):
    control = QCheckBox(text); control.setChecked(checked); return control

def csys_choice(systems):
    control = QComboBox(); control.addItem("Global", {"name":"Global","origin":(0,0,0),"axis_1":(1,0,0),"axis_2":(0,1,0)})
    for system in systems: control.addItem(system.name,{"name":system.name,"origin":system.origin,"axis_1":system.axis_1,"axis_2":system.axis_2,"system_type":system.system_type})
    return control
