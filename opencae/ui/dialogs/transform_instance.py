from opencae.ui.core.fields import FieldSpec
from opencae.ui.core.form_dialog import FormDialog


class TransformInstanceDialog(FormDialog):
    def __init__(self, instances=(), parent=None):
        default = instances[0].id if instances else ""
        super().__init__(
            "Transform Instance",
            (
                FieldSpec("instance_id", "Instance", "reference", default, tuple(instances)),
                FieldSpec("operation", "Operation", "choice", "Translate", ("Translate", "Rotate")),
                FieldSpec("x", "X / RX", "float", 0.0),
                FieldSpec("y", "Y / RY", "float", 0.0),
                FieldSpec("z", "Z / RZ", "float", 0.0),
            ),
            parent,
        )
