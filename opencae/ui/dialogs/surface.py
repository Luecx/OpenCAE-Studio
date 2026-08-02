from .region_base import RegionDialog


class SurfaceDialog(RegionDialog):
    def __init__(self, region=None, selection_provider=None, default_name="SURFACE-1", existing_names=(), parent=None):
        modes = (("Faces", "face"), ("Edges", "edge"), ("Elements", "element"))
        super().__init__("Edit Surface" if region else "Create Surface", default_name, region, selection_provider, modes, existing_names, parent)
