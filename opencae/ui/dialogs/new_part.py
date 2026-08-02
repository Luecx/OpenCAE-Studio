from PyQt6.QtWidgets import QMessageBox
from opencae.ui.core.form_dialog import FormDialog
from opencae.ui.core.fields import FieldSpec

class NewPartDialog(FormDialog):
    def __init__(self,existing_names=(),part=None,parent=None,default_name="Part-1"):
        self.existing_names={name.casefold() for name in existing_names}; self.part=part
        super().__init__('Edit Part' if part else 'New Part',(
            FieldSpec('name','Name','text',getattr(part,'name',default_name)),
            FieldSpec('part_type','Part type','choice',getattr(part,'metadata',{}).get('part_type','3D deformable'),('3D deformable','2D planar')),
        ),parent)
    def accept(self):
        name=self.values()['name']
        if not name:QMessageBox.warning(self,'Invalid part','Enter a part name.'); return
        if name.casefold() in self.existing_names and (self.part is None or name.casefold()!=self.part.name.casefold()):QMessageBox.warning(self,'Duplicate name',f"A part named '{name}' already exists."); return
        super().accept()
