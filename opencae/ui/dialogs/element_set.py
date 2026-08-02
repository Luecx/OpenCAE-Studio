from .region_base import RegionDialog


class ElementSetDialog(RegionDialog):
    def __init__(self, region=None, selection_provider=None, default_name="ELEMENT_SET-1", existing_names=(), parent=None, member_formatter=None):
        modes = ()
        super().__init__("Edit Element Set" if region else "Create Element Set", default_name, region, selection_provider, modes, existing_names, parent, member_formatter)
