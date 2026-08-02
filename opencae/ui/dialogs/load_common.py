from __future__ import annotations

from PyQt6.QtWidgets import QFormLayout,QLineEdit,QMessageBox,QVBoxLayout

from opencae.model.naming import is_unique
from opencae.ui.core.apply_dialog import ApplyDialog
from opencae.ui.core.controls import dialog_buttons
from opencae.ui.core.widgets import ReferenceSelector


class BaseLoadDialog(ApplyDialog):
    def __init__(self,title,regions=(),coordinate_systems=(),create_region=None,pick_region=None,show_region=True,show_csys=True,parent=None,default_name="",existing_names=(),entity=None):
        super().__init__(parent);self.entity=entity;self.existing_names=tuple(existing_names);self.setWindowTitle(f"{'Edit' if entity else 'Create'} {title}");self.setMinimumWidth(620);self.root=QVBoxLayout(self);self.form=QFormLayout();self.name=QLineEdit(entity.name if entity else (default_name or f"{title}-1"));self.form.addRow("Name",self.name)
        self.region=None
        if show_region:
            target=getattr(entity,"target",None) if entity else None
            if target is not None and hasattr(target,"ref"):
                current=target.ref.entity_id
            elif target is not None:
                current=target; label=f"{'Node' if hasattr(target,'node_id') else 'Element'}-{getattr(target,'node_id',getattr(target,'element_id',''))}"; regions=((label,target),*regions)
            else:
                current=regions[0].id if regions else ""
            self.region=ReferenceSelector(regions,current,create_region,pick_region);self.form.addRow("Region",self.region)
        self.csys=None
        if show_csys:
            current=entity.coordinate_system_ref.entity_id if entity and getattr(entity,"coordinate_system_ref",None) else None;self.csys=ReferenceSelector((("Global",None),*coordinate_systems),current);self.form.addRow("Coordinate system",self.csys)
        self.root.addLayout(self.form)

    def finish(self):
        buttons=dialog_buttons(include_apply=True);self.bind_buttons(buttons,True);self.root.addWidget(buttons)

    def validate(self):
        name=self.name.text().strip();current=self.entity.name if self.entity else None
        if not is_unique(name,self.existing_names,current):QMessageBox.warning(self,"Duplicate name",f"An object named '{name}' already exists.");return False
        if self.region is not None and not self.region.currentValue():QMessageBox.warning(self,"Missing region","Create or select a target region.");return False
        return True

    def common_values(self):
        values={"name":self.name.text().strip()}
        if self.region is not None:values["target_id"]=self.region.currentValue()
        if self.csys is not None:values["coordinate_system_id"]=self.csys.currentValue()
        return values

    def prepare_new(self, default_name, existing_names):
        self.entity = None
        self.existing_names = tuple(existing_names)
        self.name.setText(default_name)
        if self.region is not None:
            self.region.clear()
