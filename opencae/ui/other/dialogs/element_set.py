from .region_base import RegionDialog

class ElementSetDialog(RegionDialog):
    def __init__(self, *args, **kwargs):
        region = kwargs.pop("region", args[0] if args else None)
        default_name = kwargs.pop("default_name", "ELEMENT_SET-1")
        super().__init__("Edit Element Region" if region else "Create Element Region", default_name, region, **kwargs)
