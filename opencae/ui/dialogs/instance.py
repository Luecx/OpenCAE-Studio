from PyQt6.QtWidgets import QMessageBox

from opencae.ui.core.fields import FieldSpec
from opencae.ui.core.form_dialog import FormDialog


class InstanceDialog(FormDialog):
    def __init__(self, parts=(), create_part=None, existing_names=(), parent=None, default_name="", instance=None):
        self.existing_names={name.casefold() for name in existing_names}; self.instance=instance
        default = instance.part_ref.entity_id if instance and instance.part_ref else (parts[0].id if parts else "")
        base_name = parts[0].name if parts else "Part"
        super().__init__("Edit Part Instance" if instance else "Add Part Instance", (
            FieldSpec("name", "Instance name", "text", instance.name if instance else (default_name or f"{base_name}-1")),
            FieldSpec("part_id", "Source part", "reference", default, tuple(parts), create_callback=create_part),
        ), parent, allow_apply=True)

    def validate(self):
        values=self.values(); name=values["name"]
        if not values["part_id"]: QMessageBox.warning(self,"Missing part","Create or select a source part."); return False
        allowed=self.existing_names-{self.instance.name.casefold()} if self.instance else self.existing_names
        if name.casefold() in allowed: QMessageBox.warning(self,"Duplicate name",f"An instance named '{name}' already exists."); return False
        return True
