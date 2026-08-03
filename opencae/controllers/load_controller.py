from __future__ import annotations

from opencae.ui.core.dialog_lifecycle import show_modeless_dialog
from PyQt6.QtWidgets import QDialog, QInputDialog

from opencae.model.core import EntityRef
from opencae.model.loads import create_load, create_support
from opencae.model.entities.loads import load_region_requirement, load_selection_policy
from opencae.model.entities.supports import SUPPORT_REGION_REQUIREMENT, support_selection_policy
from opencae.model.naming import next_name
from opencae.model.regions import create_region
from opencae.model.selection import (
    RegionProjection, region_definition_error,
)
from opencae.ui.dialogs.load import LoadDialog
from opencae.ui.dialogs.support import SupportDialog
from .region_selection import begin_region_pick, region_options


class LoadController:
    def __init__(self, store, parent, part_controller=None, resource_controller=None):
        self.store = store; self.parent = parent; self.part_controller = part_controller; self._dialogs: list[QDialog] = []

    def _coordinate_systems(self): return list(self.store.project.assembly.coordinate_systems)
    def _temperature_fields(self): return [field for field in self.store.project.fields if field.location == "Nodal" and field.components == 1]

    def _require_assembly(self):
        if any(not item.suppressed for item in self.store.project.assembly.instances): return True
        self.store.message.emit("Create at least one assembly instance before defining loads or supports"); return False

    def _options(self, projection): return region_options(self.store.project, projections=(projection,))

    def _pick(self, policy):
        return lambda _owner, done, finished: begin_region_pick(self.store.project, self.parent.viewport, policy, done, finished=finished)

    def _save_region(self, projection):
        def save(_widget, definition):
            name, ok = QInputDialog.getText(self.parent, "Save Region", "Region name:", text=next_name("REGION", self.store.project.assembly.regions))
            if not ok or not name.strip(): return
            region = create_region("Region", name=name.strip(), scope="Assembly", definition=definition, preferred_projection=projection)
            self.store.add_entity(f"Created assembly region {region.name}", self.store.project.assembly.id, "regions", region)
        return save

    def _validator(self, requirement):
        return lambda definition: region_definition_error(
            self.store.project, definition, requirement
        )

    def support(self, support_type="Fixed", support=None):
        if not self._require_assembly(): return
        requirement = SUPPORT_REGION_REQUIREMENT
        dialog = SupportDialog(
            support_type=support_type, project=self.store.project, regions=self._options(RegionProjection.NODES), coordinate_systems=self._coordinate_systems(),
            create_region=self._save_region(RegionProjection.NODES),
            pick_region=self._pick(support_selection_policy()),
            parent=self.parent, default_name=next_name(support_type, self.store.project.supports),
            existing_names=[item.name for item in self.store.project.supports], support=support,
            target_validator=self._validator(requirement), target_requirement=requirement,
        )
        state = {"existing_id": getattr(support, "id", None)}
        def commit(): state["existing_id"] = self._commit_support(support_type, dialog, state["existing_id"])
        def reset():
            if support is None: state["existing_id"] = None; dialog.prepare_new(next_name(support_type, self.store.project.supports), [item.name for item in self.store.project.supports])
        self._open(dialog, commit, reset)

    def _commit_support(self, support_type, dialog, existing_id=None):
        values = dialog.values(); coordinate_system_id = values.pop("coordinate_system_id", None)
        kwargs = {"coordinate_system_ref": EntityRef(coordinate_system_id, "CoordinateSystem") if coordinate_system_id else None, **values}
        if existing_id: kwargs["id"] = existing_id
        support = create_support(support_type, **kwargs); self._commit_entity("supports", support, existing_id)
        self.store.invalidate_scene("Support updated" if existing_id else "Support created"); return support.id

    def load(self, load_type="Concentrated Load", load=None):
        if not self._require_assembly(): return
        policy = load_selection_policy(load_type)
        requirement = load_region_requirement(load_type)
        projection = requirement.projection if requirement else RegionProjection.NODES
        dialog = LoadDialog(
            load_type=load_type, project=self.store.project, regions=self._options(projection), coordinate_systems=self._coordinate_systems(), fields=self._temperature_fields(),
            create_region=self._save_region(projection), pick_region=self._pick(policy) if policy else None,
            parent=self.parent, default_name=next_name(load_type, self.store.project.loads),
            existing_names=[item.name for item in self.store.project.loads], load=load,
            target_validator=None if load_type == "Temperature" else self._validator(requirement), target_requirement=requirement,
        )
        state = {"existing_id": getattr(load, "id", None)}
        def commit(): state["existing_id"] = self._commit_load(load_type, dialog, state["existing_id"])
        def reset():
            if load is None: state["existing_id"] = None; dialog.prepare_new(next_name(load_type, self.store.project.loads), [item.name for item in self.store.project.loads])
        self._open(dialog, commit, reset)

    def _commit_load(self, load_type, dialog, existing_id=None):
        values = dialog.values(); coordinate_system_id = values.pop("coordinate_system_id", None); temperature_field_id = values.pop("temperature_field_id", None)
        kwargs = {"coordinate_system_ref": EntityRef(coordinate_system_id, "CoordinateSystem") if coordinate_system_id else None, **values}
        if existing_id: kwargs["id"] = existing_id
        if temperature_field_id: kwargs["temperature_field_ref"] = EntityRef(temperature_field_id, "FieldDefinition")
        load = create_load(load_type, **kwargs); self._commit_entity("loads", load, existing_id)
        self.store.invalidate_scene("Load updated" if existing_id else "Load created"); return load.id

    def edit(self, entity):
        from opencae.model.entities.loads import Load
        from opencae.model.entities.supports import Support
        if isinstance(entity, Load): self.load(entity.load_type, entity)
        elif isinstance(entity, Support): self.support(entity.support_type, entity)

    def _commit_entity(self, attribute, entity, existing_id):
        action = "Edited" if existing_id else "Created"
        description = f"{action} {entity.name}"
        if existing_id:
            self.store.replace_entity(description, self.store.project.id, attribute, entity)
        else:
            self.store.add_entity(description, self.store.project.id, attribute, entity)
        self.store.select(entity)

    def _finish_dialog(self, dialog):
        if hasattr(self.parent, "viewport"): self.parent.viewport.cancel_context_pick()
        if dialog in self._dialogs: self._dialogs.remove(dialog)

    def _open(self, dialog, accepted, after_apply=None):
        dialog.setModal(False); self._dialogs.append(dialog)
        viewport = getattr(self.parent, "viewport", None)
        region = getattr(dialog, "region", None)
        preview_channel = f"load-support-dialog-{id(dialog)}"

        def preview(definition):
            if viewport is not None:
                viewport.show_region_preview(
                    preview_channel, definition, color="#3296e6",
                    opacity=.58, point_size=17, show_point_labels=True,
                )

        if region is not None:
            region.value_changed.connect(preview)
        if hasattr(dialog, "applied"):
            def apply(): accepted(); after_apply() if after_apply else None
            dialog.applied.connect(apply)
        dialog.accepted.connect(accepted)

        def finish(_code):
            if viewport is not None:
                viewport.clear_region_preview(preview_channel)
            self._finish_dialog(dialog)

        dialog.finished.connect(finish)
        show_modeless_dialog(dialog)
        if region is not None:
            preview(region.definition())
