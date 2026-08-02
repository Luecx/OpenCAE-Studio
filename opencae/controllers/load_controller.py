from __future__ import annotations

from PyQt6.QtWidgets import QDialog

from opencae.model.core import EntityRef, EntityTarget, MeshElementTarget, MeshNodeTarget, members_from_selection, region_member_label, target_for_entity
from opencae.model.loads import create_load, create_support
from opencae.model.naming import next_name
from opencae.model.regions import create_region
from opencae.ui.dialogs.element_set import ElementSetDialog
from opencae.ui.dialogs.load import LoadDialog
from opencae.ui.dialogs.node_set import NodeSetDialog
from opencae.ui.dialogs.support import SupportDialog
from opencae.ui.dialogs.surface import SurfaceDialog
from .reference_pick import begin_target_pick


class LoadController:
    def __init__(self, store, parent, part_controller=None, resource_controller=None):
        self.store = store
        self.parent = parent
        self.part_controller = part_controller
        self._dialogs: list[QDialog] = []

    def _selection_labels(self):
        return members_from_selection(self.store.project, self.store.selection)

    def _regions(self, kind):
        assembly = self.store.project.assembly
        if kind == "node":
            return [*assembly.node_sets, *assembly.reference_points]
        attribute = {"element": "element_sets", "surface": "surfaces"}[kind]
        return list(getattr(assembly, attribute))

    def _coordinate_systems(self):
        return list(self.store.project.assembly.coordinate_systems)

    def _require_assembly(self):
        if any(not item.suppressed for item in self.store.project.assembly.instances):
            return True
        self.store.message.emit("Create at least one assembly instance before defining loads or supports")
        return False

    def _temperature_fields(self):
        return [field for field in self.store.project.fields if field.location == "Nodal" and field.components == 1]

    def _nested_region(self, kind, owner, done):
        mapping = {
            "node": (NodeSetDialog, "Node Set", "node_sets"),
            "surface": (SurfaceDialog, "Surface", "surfaces"),
            "element": (ElementSetDialog, "Element Set", "element_sets"),
        }
        dialog_cls, region_type, attribute = mapping[kind]
        owner.hide()
        collection = getattr(self.store.project.assembly, attribute)
        prefix = {"node_sets": "NODE_SET", "element_sets": "ELEMENT_SET", "surfaces": "SURFACE"}[attribute]
        dialog = dialog_cls(
            selection_provider=self._selection_labels,
            default_name=next_name(prefix, collection),
            existing_names=[item.name for item in collection],
            parent=self.parent,
            member_formatter=lambda member: region_member_label(self.store.project, member),
        )
        previous = self.parent.viewport.selection_mode
        if getattr(dialog, "selection_mode", None) is not None:
            self.parent.viewport.set_selection_mode(dialog.mode())
        slot = lambda _value: dialog.update_selection()
        self.store.selection_changed.connect(slot)

        def restore():
            try:
                self.store.selection_changed.disconnect(slot)
            except Exception:
                pass
            if getattr(dialog, "selection_mode", None) is not None:
                self.parent.viewport.set_selection_mode(previous)
            owner.show()
            owner.raise_()
            owner.activateWindow()

        def commit(values):
            region = create_region(region_type, scope="Assembly", **values)
            self.store.mutate(f"Created assembly {region.name}", lambda project: getattr(project.assembly, attribute).append(region))
            done(region)
            dialog.close()

        if getattr(dialog, "selection_mode", None) is not None:
            dialog.selection_mode.currentTextChanged.connect(lambda _text: self.parent.viewport.set_selection_mode(dialog.mode()))
        dialog.committed.connect(commit)
        dialog.finished.connect(lambda _code: restore())
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def support(self, support_type="Fixed", support=None):
        if not self._require_assembly():
            return
        create = lambda owner, done: self._nested_region("node", owner, done)
        regions = self._regions("node")
        pick = lambda _owner, done: begin_target_pick(self.store.project,self.parent.viewport,regions,{"point","face","node"},done,mesh_nodes=True)
        dialog = SupportDialog(
            support_type=support_type, regions=regions, coordinate_systems=self._coordinate_systems(),
            create_region=create, pick_region=pick, parent=self.parent,
            default_name=next_name(support_type, self.store.project.supports),
            existing_names=[item.name for item in self.store.project.supports], support=support,
        )
        state = {"existing": support}
        def commit(): state["existing"] = self._commit_support(support_type, dialog, state["existing"])
        def reset_after_apply():
            if support is not None:
                return
            state["existing"] = None
            dialog.prepare_new(next_name(support_type, self.store.project.supports), [item.name for item in self.store.project.supports])
        self._open(dialog, commit, reset_after_apply)

    def _commit_support(self, support_type, dialog, existing=None):
        values = dialog.values()
        target_value = values.pop("target_id")
        target = self._target_value(target_value)
        coordinate_system_id = values.pop("coordinate_system_id", None)
        kwargs = {
            "target": target,
            "coordinate_system_ref": EntityRef(coordinate_system_id, "CoordinateSystem") if coordinate_system_id else None,
            **values,
        }
        if existing is not None:
            kwargs["id"] = existing.id
        support = create_support(support_type, **kwargs)
        self._commit_entity("supports", support, existing)
        self.store.invalidate_scene("Support updated" if existing else "Support created")
        return support

    def load(self, load_type="Concentrated Load", load=None):
        if not self._require_assembly():
            return
        kind = {
            "Concentrated Load": "node",
            "Pressure": "surface",
            "Surface Traction": "surface",
            "Volume Load": "element",
            "Inertia Load": "element",
        }.get(load_type, "node")
        create = lambda owner, done: self._nested_region(kind, owner, done)
        regions = self._regions(kind)
        allowed = {"point", "face"} if kind == "node" else ({"face"} if kind == "surface" else {"cell", "element"})
        pick = lambda _owner, done: begin_target_pick(self.store.project,self.parent.viewport,regions,allowed | ({"element"} if load_type=="Volume Load" else set()),done,mesh_nodes=load_type=="Concentrated Load",mesh_elements=load_type=="Volume Load")
        dialog = LoadDialog(
            load_type=load_type, regions=regions, coordinate_systems=self._coordinate_systems(),
            fields=self._temperature_fields(), create_region=create, pick_region=pick, parent=self.parent,
            default_name=next_name(load_type, self.store.project.loads),
            existing_names=[item.name for item in self.store.project.loads], load=load,
        )
        state = {"existing": load}
        def commit(): state["existing"] = self._commit_load(load_type, dialog, state["existing"])
        def reset_after_apply():
            if load is not None:
                return
            state["existing"] = None
            dialog.prepare_new(next_name(load_type, self.store.project.loads), [item.name for item in self.store.project.loads])
        self._open(dialog, commit, reset_after_apply)

    def _commit_load(self, load_type, dialog, existing=None):
        values = dialog.values()
        target_id = values.pop("target_id", None)
        coordinate_system_id = values.pop("coordinate_system_id", None)
        temperature_field_id = values.pop("temperature_field_id", None)
        kwargs = {
            "target": self._target_value(target_id) if target_id else None,
            "coordinate_system_ref": EntityRef(coordinate_system_id, "CoordinateSystem") if coordinate_system_id else None,
            **values,
        }
        if existing is not None:
            kwargs["id"] = existing.id
        if temperature_field_id:
            kwargs["temperature_field_ref"] = EntityRef(temperature_field_id, "FieldDefinition")
        load = create_load(load_type, **kwargs)
        self._commit_entity("loads", load, existing)
        self.store.invalidate_scene("Load updated" if existing else "Load created")
        return load

    def edit(self, entity):
        from opencae.model.entities.loads import Load
        from opencae.model.entities.supports import Support
        if isinstance(entity, Load):
            self.load(entity.load_type, entity)
        elif isinstance(entity, Support):
            self.support(entity.support_type, entity)

    def _target_value(self, value):
        if isinstance(value, (EntityTarget, MeshNodeTarget, MeshElementTarget)):
            return value
        return target_for_entity(self._resolve_target(value))

    def _resolve_target(self, entity_id):
        target = self.store.project.try_resolve(entity_id)
        if target is None:
            raise ValueError(f"The selected target '{entity_id}' no longer exists")
        return target

    def _commit_entity(self, attribute, entity, existing):
        action = "Edited" if existing else "Created"

        def apply(project):
            collection = getattr(project, attribute)
            if existing is None:
                collection.append(entity)
                return
            index = next((index for index, item in enumerate(collection) if item.id == existing.id), None)
            if index is None:
                raise ValueError(f"Cannot edit missing {type(existing).__name__} '{existing.name}'")
            collection[index] = entity

        self.store.mutate(f"{action} {entity.name}", apply)

    def _finish_dialog(self, dialog):
        if hasattr(self.parent, "viewport"):
            self.parent.viewport.cancel_context_pick()
        if dialog in self._dialogs:
            self._dialogs.remove(dialog)

    def _open(self, dialog, accepted, after_apply=None):
        dialog.setModal(False)
        self._dialogs.append(dialog)
        if hasattr(dialog, "applied"):
            def apply():
                accepted()
                if after_apply:
                    after_apply()
            dialog.applied.connect(apply)
        dialog.accepted.connect(accepted)
        dialog.finished.connect(lambda _code: self._finish_dialog(dialog))
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
