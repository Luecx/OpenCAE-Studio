from .region_base import RegionDialog

class SurfaceDialog(RegionDialog):
    def __init__(self, *args, **kwargs):
        region = kwargs.pop("region", args[0] if args else None)
        default_name = kwargs.pop("default_name", "SURFACE-1")
        super().__init__("Edit Surface Region" if region else "Create Surface Region", default_name, region, **kwargs)
