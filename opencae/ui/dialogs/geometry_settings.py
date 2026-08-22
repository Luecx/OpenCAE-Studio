from opencae.ui.core.fields import FieldSpec
from opencae.ui.core.form_dialog import FormDialog


class GeometrySettingsDialog(FormDialog):
    def __init__(self, settings, parent=None):
        super().__init__(
            "Geometry Settings",
            (
                FieldSpec("heal_on_import", "Heal on import", "bool", settings.heal_on_import),
                FieldSpec("tolerance", "OCC tolerance", "float", settings.tolerance, minimum=1e-12, decimals=10, quantity="length"),
                FieldSpec("sew_faces", "Sew faces", "bool", settings.sew_faces),
                FieldSpec("make_solids", "Make solids", "bool", settings.make_solids),
                FieldSpec("remove_degenerate", "Repair degenerated entities", "bool", settings.remove_degenerate),
                FieldSpec("display_size_factor", "Display tessellation factor", "float", settings.display_size_factor, minimum=0.001, maximum=0.2),
            ),
            parent,
            width=480,
        )
