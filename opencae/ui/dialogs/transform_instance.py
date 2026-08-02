from opencae.ui.core.form_dialog import FormDialog
from opencae.ui.core.fields import FieldSpec

class TransformInstanceDialog(FormDialog):
    def __init__(self,instances=(),parent=None):
        super().__init__('Transform Instance',(
            FieldSpec('instance_name','Instance','choice',instances[0] if instances else '',tuple(instances)), FieldSpec('operation','Operation','choice','Translate',('Translate','Rotate')),
            FieldSpec('x','X / RX','float',0.0),FieldSpec('y','Y / RY','float',0.0),FieldSpec('z','Z / RZ','float',0.0),
        ),parent)
