from __future__ import annotations

from opencae.model.regions import create_region
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

    def _open(self, dialog_cls, target, kind):
        collection = getattr(self.store.project.assembly, target)
        prefix = {"node_sets": "NODE_SET", "element_sets": "ELEMENT_SET", "surfaces": "SURFACE"}[target]
        dialog = dialog_cls(selection_provider=self.controller._selection_labels, default_name=next_name(prefix, collection), existing_names=[i.name for i in collection], parent=self.parent)
        self.session.open(dialog, lambda values: self._commit(target, kind, values))

    def _commit(self, target, kind, values):
        region = create_region(kind, scope="Assembly", **values)

        def apply(project):
            collection = getattr(project.assembly, target)
            existing = next(
                (item for item in collection if item.name.lower() == region.name.lower()),
                None,
            )
            if existing:
                collection[collection.index(existing)] = region
            else:
                collection.append(region)

        self.store.mutate(f"Created assembly {region.name}", apply)
