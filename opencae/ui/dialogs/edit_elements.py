from opencae.ui.core.form_dialog import FormDialog
from opencae.ui.core.fields import FieldSpec

class EditElementsDialog(FormDialog):
    def __init__(self, parent=None):
        super().__init__('Edit Elements', (FieldSpec('category','Element category','choice','Solid Elements',('Line Elements', 'Shell Elements', '2D Elements', 'Solid Elements')), FieldSpec('topology','Topology','choice','Hexahedra',('Lines', 'Triangles', 'Quadrilaterals', 'Tetrahedra', 'Pyramids', 'Pentahedra', 'Hexahedra')), FieldSpec('order','Geometric order','choice','Linear',('Linear', 'Quadratic')), FieldSpec('formulation','Formulation','choice','Standard',('Standard', 'Reduced integration', 'Hybrid', 'Incompatible modes')), FieldSpec('count','Element count','int',0,()),), parent)
