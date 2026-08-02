from PyQt6.QtWidgets import QDialog

from opencae.model.loads import create_load, create_support
from opencae.model.naming import next_name
from opencae.model.regions import create_region
from opencae.ui.dialogs.element_set import ElementSetDialog
from opencae.ui.dialogs.load import LoadDialog
from opencae.ui.dialogs.node_set import NodeSetDialog
from opencae.ui.dialogs.support import SupportDialog
from opencae.ui.dialogs.surface import SurfaceDialog


class LoadController:
    def __init__(self, store, parent, part_controller=None, resource_controller=None):
        self.store = store; self.parent = parent; self.part_controller = part_controller; self._dialogs = []

    def _selection_labels(self):
        selection = self.store.selection; items = selection.get("entities", [selection]) if isinstance(selection, dict) else []
        return [item.get("name") for item in items if item.get("name")]

    def _regions(self, kind):
        attribute = {"node": "node_sets", "element": "element_sets", "surface": "surfaces"}[kind]
        return [region.name for region in getattr(self.store.project.assembly, attribute)]

    def _coordinate_systems(self): return [item.name for item in self.store.project.assembly.coordinate_systems]

    def _require_assembly(self):
        if any(not item.suppressed for item in self.store.project.assembly.instances): return True
        self.store.message.emit("Create at least one assembly instance before defining loads or supports"); return False

    def _temperature_fields(self):
        return [field.name for field in self.store.project.fields if field.location == "Nodal" and field.components == 1]

    def _nested_region(self, kind, owner, done):
        mapping = {"node": (NodeSetDialog, "Node Set", "node_sets"), "surface": (SurfaceDialog, "Surface", "surfaces"), "element": (ElementSetDialog, "Element Set", "element_sets")}
        dialog_cls, region_type, attribute = mapping[kind]; owner.hide()
        collection = getattr(self.store.project.assembly, attribute); prefix = {"node_sets": "NODE_SET", "element_sets": "ELEMENT_SET", "surfaces": "SURFACE"}[attribute]
        dialog = dialog_cls(selection_provider=self._selection_labels, default_name=next_name(prefix, collection), existing_names=[i.name for i in collection], parent=self.parent); previous = self.parent.viewport.selection_mode
        self.parent.viewport.set_selection_mode(dialog.mode()); slot = lambda _value: dialog.update_selection(); self.store.selection_changed.connect(slot)
        def restore():
            try: self.store.selection_changed.disconnect(slot)
            except Exception: pass
            self.parent.viewport.set_selection_mode(previous); owner.show(); owner.raise_(); owner.activateWindow()
        def commit(values):
            region = create_region(region_type, scope="Assembly", **values); target = getattr(self.store.project.assembly, attribute)
            self.store.mutate(f"Created assembly {region.name}", lambda project: target.append(region)); done(region.name); dialog.close()
        dialog.selection_mode.currentTextChanged.connect(lambda _text: self.parent.viewport.set_selection_mode(dialog.mode()))
        dialog.committed.connect(commit); dialog.finished.connect(lambda _code: restore()); dialog.show(); dialog.raise_(); dialog.activateWindow()

    def support(self, support_type="Fixed"):
        if not self._require_assembly(): return
        create = lambda owner, done: self._nested_region("node", owner, done)
        dialog = SupportDialog(support_type, self._regions("node"), self._coordinate_systems(), create, self.parent, next_name(support_type, self.store.project.supports), [i.name for i in self.store.project.supports])
        self._open(dialog, lambda: self._commit_support(support_type, dialog))

    def _commit_support(self, support_type, dialog):
        support = create_support(support_type, **dialog.values())
        self.store.mutate(f"Created {support.name}", lambda project: project.supports.append(support)); self.store.invalidate_scene("Support created")

    def load(self, load_type="Concentrated Load"):
        if not self._require_assembly(): return
        kind = {"Concentrated Load": "node", "Pressure": "surface", "Surface Traction": "surface", "Volume Load": "element", "Inertia Load": "element"}.get(load_type, "node")
        create = lambda owner, done: self._nested_region(kind, owner, done)
        dialog = LoadDialog(load_type, self._regions(kind), self._coordinate_systems(), self._temperature_fields(), create, self.parent, next_name(load_type, self.store.project.loads), [i.name for i in self.store.project.loads])
        self._open(dialog, lambda: self._commit_load(load_type, dialog))

    def _commit_load(self, load_type, dialog):
        load = create_load(load_type, **dialog.values())
        self.store.mutate(f"Created {load.name}", lambda project: project.loads.append(load)); self.store.invalidate_scene("Load created")

    def _open(self, dialog, accepted):
        dialog.setModal(False); self._dialogs.append(dialog); dialog.accepted.connect(accepted)
        dialog.finished.connect(lambda _code: self._dialogs.remove(dialog) if dialog in self._dialogs else None)
        dialog.show(); dialog.raise_(); dialog.activateWindow()
