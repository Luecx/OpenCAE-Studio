from PyQt6.QtWidgets import QFormLayout,QLineEdit,QMessageBox,QVBoxLayout

from opencae.model.naming import is_unique
from opencae.ui.core.apply_dialog import ApplyDialog
from opencae.ui.core.controls import dialog_buttons
from opencae.ui.core.widgets import ComponentsWidget,ReferenceSelector


class SupportDialog(ApplyDialog):
    def __init__(self,support_type,regions=(),coordinate_systems=(),create_region=None,pick_region=None,parent=None,default_name="",existing_names=(),support=None):
        super().__init__(parent);self.support_type=support_type;self.support=support;self.existing_names=tuple(existing_names);self.setWindowTitle(f"{'Edit' if support else 'Create'} {support_type}");self.setMinimumWidth(600);root=QVBoxLayout(self);form=QFormLayout();self.name=QLineEdit(support.name if support else (default_name or f"{support_type}-1"));target=getattr(support,"target",None) if support else None
        if target is not None and hasattr(target,"ref"):current=target.ref.entity_id
        elif target is not None:current=target;label=f"Node-{getattr(target,'node_id','')}";regions=((label,target),*regions)
        else:current=regions[0].id if regions else ""
        self.region=ReferenceSelector(regions,current,create_region,pick_region);csys=support.coordinate_system_ref.entity_id if support and support.coordinate_system_ref else None;self.csys=ReferenceSelector((("Global",None),*coordinate_systems),csys);form.addRow("Name",self.name);form.addRow("Region",self.region);form.addRow("Coordinate system",self.csys);root.addLayout(form);defaults=getattr(support,"components",([0.0]*6 if support_type=="Fixed" else [None]*6));self.components=ComponentsWidget(("Ux","Uy","Uz","Rx","Ry","Rz"),defaults,checkable=True,editable=support_type!="Fixed");root.addWidget(self.components);buttons=dialog_buttons(include_apply=True);self.bind_buttons(buttons,True);root.addWidget(buttons)

    def validate(self):
        name=self.name.text().strip()
        if not is_unique(name,self.existing_names,self.support.name if self.support else None):QMessageBox.warning(self,"Duplicate name",f"A support named '{name}' already exists.");return False
        if not self.region.currentValue():QMessageBox.warning(self,"Missing region","Create or select a target region.");return False
        return True

    def values(self):return {"name":self.name.text().strip(),"target_id":self.region.currentValue(),"coordinate_system_id":self.csys.currentValue(),"components":self.components.values()}

    def prepare_new(self, default_name, existing_names):
        self.support = None
        self.existing_names = tuple(existing_names)
        self.name.setText(default_name)
        self.region.clear()
