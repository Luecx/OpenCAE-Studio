from __future__ import annotations

from opencae.model.regions import create_region
from opencae.model.core import region_member_label
from opencae.model.naming import next_name
from opencae.ui.dialogs.element_set import ElementSetDialog
from opencae.ui.dialogs.node_set import NodeSetDialog
from opencae.ui.dialogs.surface import SurfaceDialog

from .region_dialog_session import RegionDialogSession


class AssemblyRegions:
    def __init__(self, controller):
        self.controller = controller
        self.store = controller.store
        self.parent = controller.parent
        self.dialogs = []
        self.session = RegionDialogSession(self.store, self.parent, self.dialogs)

    def node_set(self):
        self._open(NodeSetDialog, "node_sets", "Node Set")

    def element_set(self):
        self._open(ElementSetDialog, "element_sets", "Element Set")

    def surface(self):
        self._open(SurfaceDialog, "surfaces", "Surface")

    def edit(self, region):
        specifications = (
            ("node_sets", "Node Set", NodeSetDialog),
            ("element_sets", "Element Set", ElementSetDialog),
            ("surfaces", "Surface", SurfaceDialog),
        )
        for target, kind, dialog_cls in specifications:
            if region in getattr(self.store.project.assembly, target):
                self._open(dialog_cls, target, kind, region)
                return True
        return False

    def _open(self, dialog_cls, target, kind, region=None):
        collection = getattr(self.store.project.assembly, target)
        prefix = {"node_sets": "NODE_SET", "element_sets": "ELEMENT_SET", "surfaces": "SURFACE"}[target]
        dialog = dialog_cls(
            region=region,
            selection_provider=self.controller._selection_labels,
            default_name=next_name(prefix, collection),
            existing_names=[item.name for item in collection],
            parent=self.parent,
            member_formatter=lambda member: region_member_label(self.store.project, member),
        )
        self.session.open(dialog, lambda values: self._commit(target, kind, region, values))

    def _commit(self, target, kind, existing, values):
        if existing is not None:
            values["id"] = existing.id
        region = create_region(kind, scope="Assembly", **values)

        def apply(project):
            collection = getattr(project.assembly, target)
            if existing is None:
                collection.append(region)
            else:
                index = next(i for i, item in enumerate(collection) if item.id == existing.id)
                collection[index] = region

        action = "Edited" if existing else "Created"
        self.store.mutate(f"{action} assembly {region.name}", apply)
        self.store.select(region)
