from opencae.ui.core.fields import FieldSpec
from opencae.ui.core.form_dialog import FormDialog


class ProjectSettingsDialog(FormDialog):
    def __init__(self, unit_systems, parent=None):
        names = tuple(item.name for item in unit_systems)
        super().__init__("Project Settings", (
            FieldSpec("name", "Project name", "text", "Bracket Study", ()),
            FieldSpec("unit_system", "Unit system", "choice", names[0] if names else "", names),
            FieldSpec("autosave", "Enable autosave", "bool", True, ()),
        ), parent)
