from opencae.ui.core.apply_form_dialog import ApplyFormDialog
from opencae.ui.core.fields import FieldSpec


class DefaultSeedDialog(ApplyFormDialog):
    def __init__(self, seed=None, parent=None):
        metadata = seed.metadata if seed else {}
        super().__init__(
            "Seed Part",
            (
                FieldSpec("name", "Name", "text", seed.name if seed else "Default Seed"),
                FieldSpec("size", "Approximate global size", "float", seed.size if seed else 5.0, minimum=1e-12),
                FieldSpec("deviation", "Deviation factor", "float", metadata.get("deviation", 0.1), minimum=0.0),
                FieldSpec("minimum", "Minimum size factor", "float", metadata.get("minimum", 0.1), minimum=0.0001, maximum=1.0),
            ),
            parent,
        )
