from opencae.ui.core.apply_form_dialog import ApplyFormDialog
from opencae.ui.core.fields import FieldSpec


class EdgeSeedDialog(ApplyFormDialog):
    def __init__(self, selected_edges=(), seed=None, parent=None):
        targets = selected_edges or tuple(map(str, seed.targets)) if seed else ()
        super().__init__(
            "Seed Edges",
            (
                FieldSpec("name", "Name", "text", seed.name if seed else "Edge Seed"),
                FieldSpec("targets", "Selected edges", "text", ", ".join(targets), read_only=True),
                FieldSpec("method", "Method", "choice", seed.method if seed else "Number of divisions", ("Size", "Number of divisions")),
                FieldSpec("size", "Approximate size", "float", seed.size if seed else 1.0, minimum=1e-12),
                FieldSpec("divisions", "Number of divisions", "int", seed.divisions if seed and seed.divisions else 10, minimum=1, maximum=1_000_000),
                FieldSpec("bias", "Distribution", "choice", seed.bias if seed else "None", ("None", "Single", "Double")),
                FieldSpec("bias_factor", "Bias factor", "float", seed.bias_factor if seed else 1.0, minimum=1.0),
            ),
            parent,
            width=540,
        )

    def set_selected_edges(self, labels):
        self._editors["targets"].setText(", ".join(labels))

    def set_divisions(self, value: int):
        self._editors["method"].setCurrentText("Number of divisions")
        self._editors["divisions"].setValue(max(1, int(value)))
