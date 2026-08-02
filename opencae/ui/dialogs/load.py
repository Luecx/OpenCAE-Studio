from __future__ import annotations

from PyQt6.QtWidgets import QCheckBox,QDoubleSpinBox,QGroupBox,QVBoxLayout

from opencae.ui.core.widgets import ComponentsWidget,ReferenceSelector
from .load_common import BaseLoadDialog


class LoadDialog(BaseLoadDialog):
    def __init__(self,load_type,regions=(),coordinate_systems=(),fields=(),create_region=None,pick_region=None,parent=None,default_name="",existing_names=(),load=None):
        show_csys=load_type in {"Concentrated Load","Surface Traction","Volume Load"};show_region=load_type!="Temperature";super().__init__(load_type,regions,coordinate_systems,create_region,pick_region,show_region,show_csys,parent,default_name,existing_names,load);self.load_type=load_type;self.components=None;self.scalar=None;self.temperature_field=None;self.inertia=None
        if load_type=="Concentrated Load":self.components=ComponentsWidget(("Fx","Fy","Fz","Mx","My","Mz"),getattr(load,"components",[0.0]*6));self.root.addWidget(self.components)
        elif load_type in {"Surface Traction","Volume Load"}:self.components=ComponentsWidget(("Fx","Fy","Fz"),getattr(load,"components",[0.0]*3));self.root.addWidget(self.components)
        elif load_type=="Pressure":self.scalar=self._number(getattr(load,"pressure",1.0));self.form.addRow("Pressure",self.scalar)
        elif load_type=="Temperature":
            self.scalar=self._number(getattr(load,"reference_temperature",0.0));self.form.addRow("Reference temperature",self.scalar);current=load.temperature_field_ref.entity_id if load and getattr(load,"temperature_field_ref",None) else (fields[0].id if fields else "");self.temperature_field=ReferenceSelector(fields,current);self.form.addRow("Temperature field",self.temperature_field)
        elif load_type=="Inertia Load":
            values=(getattr(load,"center",(0,0,0)),getattr(load,"center_acceleration",(0,0,0)),getattr(load,"angular_velocity",(0,0,0)),getattr(load,"angular_acceleration",(0,0,0)));self.inertia=[ComponentsWidget(("X","Y","Z"),value) for value in values]
            for title,widget in zip(("Center","Center acceleration","Angular velocity","Angular acceleration"),self.inertia):group=QGroupBox(title);layout=QVBoxLayout(group);layout.addWidget(widget);self.root.addWidget(group)
            self.point_masses=QCheckBox("Consider point masses");self.point_masses.setChecked(getattr(load,"consider_point_masses",False));self.root.addWidget(self.point_masses)
        self.finish()

    @staticmethod
    def _number(value):widget=QDoubleSpinBox();widget.setDecimals(12);widget.setRange(-1e300,1e300);widget.setValue(value);return widget

    def values(self):
        values=self.common_values()
        if self.components is not None:values["components"]=self.components.values()
        if self.load_type=="Pressure":values["pressure"]=self.scalar.value()
        if self.load_type=="Temperature":values.update(reference_temperature=self.scalar.value(),temperature_field_id=self.temperature_field.currentValue())
        if self.load_type=="Inertia Load":
            keys=("center","center_acceleration","angular_velocity","angular_acceleration");values.update({key:tuple(widget.values()) for key,widget in zip(keys,self.inertia)});values["consider_point_masses"]=self.point_masses.isChecked()
        return values
