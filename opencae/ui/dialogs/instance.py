from PyQt6.QtWidgets import QMessageBox
from opencae.ui.core.form_dialog import FormDialog
from opencae.ui.core.fields import FieldSpec

class InstanceDialog(FormDialog):
    def __init__(self, part_names=(), create_part=None, existing_names=(), parent=None, default_name=""):
        self.existing_names={name.casefold() for name in existing_names}
        default=part_names[0] if part_names else ''
        super().__init__('Add Part Instance',(FieldSpec('name','Instance name','text',default_name or f'{default or "Part"}-1'),FieldSpec('part_name','Source part','reference',default,tuple(part_names),create_callback=create_part)),parent)
    def accept(self):
        values=self.values(); name=values['name']
        if not values['part_name']: QMessageBox.warning(self,'Missing part','Create or select a source part.'); return
        if name.casefold() in self.existing_names: QMessageBox.warning(self,'Duplicate name',f"An instance named '{name}' already exists."); return
        super().accept()
