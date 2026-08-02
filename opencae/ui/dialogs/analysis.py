from opencae.ui.core.fields import FieldSpec
from opencae.ui.core.form_dialog import FormDialog


class AnalysisDialog(FormDialog):
    def __init__(self, parent=None):
        super().__init__(
            "Create Analysis",
            (
                FieldSpec("name", "Name", "text", "Analysis-1", ()),
                FieldSpec("analysis_type", "Type", "choice", "Linear Static", ("Linear Static", "Nonlinear Static", "Eigenfrequency", "Linear Buckling", "Transient")),
            ),
            parent,
        )
