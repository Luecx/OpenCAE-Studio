from .region_base import RegionDialog

class NodeSetDialog(RegionDialog):
    def __init__(self, *args, **kwargs):
        region = kwargs.pop("region", args[0] if args else None)
        default_name = kwargs.pop("default_name", "NODE_SET-1")
        super().__init__("Edit Node Region" if region else "Create Node Region", default_name, region, **kwargs)
