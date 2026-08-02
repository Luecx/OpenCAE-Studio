from opencae.ui.core.fields import FieldSpec
from opencae.ui.core.form_dialog import FormDialog


class MeshControlDialog(FormDialog):
    def __init__(self, selected_entities: tuple[str, ...] = (), control=None, parent=None):
        super().__init__(
            "Mesh Control",
            (
                FieldSpec("name", "Name", "text", control.name if control else "Mesh Control-1"),
                FieldSpec("scope", "Scope", "choice", control.scope if control else "Cell", ("Edge", "Face", "Cell")),
                FieldSpec("targets", "Targets", "text", ", ".join(selected_entities or tuple(map(str, control.targets)) if control else ())),
                FieldSpec("topology", "Preferred topology", "choice", control.topology if control else "Tetrahedral", ("Line", "Triangular", "Quadrilateral", "Tetrahedral", "Pyramidal", "Pentahedral", "Hexahedral")),
                FieldSpec("technique", "Technique", "choice", control.technique if control else "Free", ("Free", "Structured", "Transfinite", "Recombine")),
            ),
            parent,
            width=500,
        )
