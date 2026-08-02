from opencae.ui.core.fields import FieldSpec
from opencae.ui.core.form_dialog import FormDialog


class MeshSettingsDialog(FormDialog):
    def __init__(self, settings, parent=None):
        super().__init__(
            "Gmsh Mesh Settings",
            (
                FieldSpec("algorithm_2d", "2D algorithm", "choice", settings.algorithm_2d, ("MeshAdapt", "Automatic", "Delaunay", "Frontal-Delaunay", "Frontal-Delaunay for Quads")),
                FieldSpec("algorithm_3d", "3D algorithm", "choice", settings.algorithm_3d, ("Delaunay", "Frontal", "HXT")),
                FieldSpec("element_order", "Element order", "choice", str(settings.element_order), ("1", "2")),
                FieldSpec("optimize", "Optimize mesh", "bool", settings.optimize),
                FieldSpec("high_order_optimize", "Optimize high-order mesh", "bool", settings.high_order_optimize),
                FieldSpec("recombine_all", "Recombine all surfaces", "bool", settings.recombine_all),
                FieldSpec("num_threads", "Gmsh threads (0 = automatic)", "int", settings.num_threads, minimum=0, maximum=256),
            ),
            parent,
            width=500,
        )

    def values(self):
        values = super().values()
        values["element_order"] = int(values["element_order"])
        return values
