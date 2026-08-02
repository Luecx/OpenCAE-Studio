from .region_base import RegionDialog


class NodeSetDialog(RegionDialog):
    def __init__(self, region=None, selection_provider=None, default_name="NODE_SET-1", existing_names=(), parent=None, member_formatter=None):
        modes = ()
        super().__init__("Edit Node Set" if region else "Create Node Set", default_name, region, selection_provider, modes, existing_names, parent, member_formatter)
