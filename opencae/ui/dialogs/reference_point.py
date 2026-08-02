from PyQt6.QtWidgets import QMessageBox

from opencae.model.naming import is_unique
from opencae.ui.core.fields import FieldSpec
from opencae.ui.core.form_dialog import FormDialog


class ReferencePointDialog(FormDialog):
    def __init__(self, default_name="RP-1", existing_names=(), parent=None):
        self.existing_names = tuple(existing_names)
        super().__init__("Create Reference Point", (
            FieldSpec("name", "Name", "text", default_name, ()), FieldSpec("x", "X", "float", 0.0, ()),
            FieldSpec("y", "Y", "float", 0.0, ()), FieldSpec("z", "Z", "float", 0.0, ()),
        ), parent)

    def accept(self):
        name = self.values()["name"]
        if not is_unique(name, self.existing_names): QMessageBox.warning(self, "Duplicate name", f"A reference point named '{name}' already exists."); return
        super().accept()
