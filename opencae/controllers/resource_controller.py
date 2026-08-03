from __future__ import annotations

from copy import deepcopy

from PyQt6.QtWidgets import QDialog, QMessageBox

from opencae.model.entities.fields import FieldDefinition
from opencae.model.naming import next_name
from opencae.model.selection import RegionProjection
from opencae.model.resources import Material, create_profile, create_section
from opencae.ui.dialogs.field_definition import FieldDefinitionDialog
from opencae.ui.dialogs.material import MaterialDialog
from opencae.ui.dialogs.material_property import MaterialPropertyDialog
from opencae.ui.dialogs.profile import ProfileDialog
from opencae.ui.dialogs.section import SectionDialog


class ResourceController:
    def __init__(self, store, parent):
        self.store = store
        self.parent = parent

    def material(self): return self._material_dialog()
    def profile(self, kind=None): return self._profile_dialog(initial_type=kind)
    def section(self, kind=None): return self._section_dialog(initial_type=kind)
    def field(self): return self._field_dialog()

    def selected_material(self):
        selected = self.store.selection
        return selected if isinstance(selected, Material) else (self.store.project.materials[-1] if self.store.project.materials else None)

    def set_behavior(self, category):
        material = self.selected_material()
        if material is None:
            QMessageBox.information(self.parent, "No material", "Create or select a material first.")
            return
        current = next((item for item in material.behaviors if item.category == category), None)
        dialog = MaterialPropertyDialog(current, self.parent, category)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        behavior = dialog.behavior_value()

        stored = self.store.project.try_resolve(material.id)
        if stored is None:
            self.store.message.emit("The selected material no longer exists")
            return
        replacement = deepcopy(stored)
        replacement.behaviors = [item for item in replacement.behaviors if item.category != category]
        replacement.behaviors.append(behavior)
        self.store.replace_entity(f"Set {category} for {material.name}", self.store.project.id, "materials", replacement)

    def _material_dialog(self, material=None, parent=None):
        project = self.store.project
        dialog = MaterialDialog(material, [item.name for item in project.materials], parent or self.parent, next_name("Material", project.materials))
        state = {"existing": material}

        def commit():
            current = state["existing"]
            values = dialog.values()
            if current: values["id"] = current.id
            value = Material(**values)
            self._replace_or_append("materials", current, value, f"{'Edited' if current else 'Created'} material {value.name}")
            state["existing"] = value
            self.store.select(value)

        def apply():
            commit()
            if material is None:
                state["existing"] = None
                dialog.prepare_new(next_name("Material", project.materials), [item.name for item in project.materials])
        dialog.applied.connect(apply)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            commit()
        return state["existing"]

    def _profile_dialog(self, profile=None, initial_type=None, parent=None):
        project = self.store.project
        dialog = ProfileDialog(profile, [item.name for item in project.profiles], parent or self.parent, initial_type, next_name("Profile", project.profiles))
        state = {"existing": profile}

        def commit():
            current = state["existing"]
            values = dialog.values(); kind = values.pop("profile_type")
            if current: values["id"] = current.id
            value = create_profile(kind, **values)
            self._replace_or_append("profiles", current, value, f"{'Edited' if current else 'Created'} profile {value.name}")
            state["existing"] = value
            self.store.select(value)

        def apply():
            commit()
            if profile is None:
                state["existing"] = None
                dialog.prepare_new(next_name("Profile", project.profiles), [item.name for item in project.profiles])
        dialog.applied.connect(apply)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            commit()
        return state["existing"]

    def _section_dialog(self, section=None, initial_type=None, parent=None):
        project = self.store.project
        owner = parent or self.parent
        def create_material(child, done): done(self._material_dialog(parent=child or owner))
        def create_profile(child, done): done(self._profile_dialog(parent=child or owner))
        dialog = SectionDialog(
            project.materials, project.profiles, create_material, create_profile, section,
            [item.name for item in project.sections], owner, initial_type, next_name("Section", project.sections),
        )
        state = {"existing": section}

        def commit():
            current = state["existing"]
            values = dialog.values(); kind = values.pop("section_type")
            if current: values["id"] = current.id
            value = create_section(kind, **values)
            self._replace_or_append("sections", current, value, f"{'Edited' if current else 'Created'} section {value.name}")
            state["existing"] = value
            self.store.select(value)

        def apply():
            commit()
            if section is None:
                state["existing"] = None
                dialog.prepare_new(next_name("Section", project.sections), [item.name for item in project.sections])
        dialog.applied.connect(apply)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            commit()
        return state["existing"]

    def _field_dialog(self, field=None, parent=None):
        project = self.store.project
        regions = []
        allowed = {RegionProjection.NODES, RegionProjection.ELEMENTS, None}
        for part in project.parts:
            regions.extend(
                (f"{part.name}.{item.name}", item.id)
                for item in part.regions
                if item.preferred_projection in allowed
            )
        regions.extend(
            (f"Assembly.{item.name}", item.id)
            for item in project.assembly.regions
            if item.preferred_projection in allowed
        )
        dialog = FieldDefinitionDialog(field, [item.name for item in project.fields], regions, parent or self.parent, next_name("Field", project.fields))
        state = {"existing": field}

        def commit():
            current = state["existing"]
            values = dialog.values()
            if current: values["id"] = current.id
            value = FieldDefinition(**values)
            self._replace_or_append("fields", current, value, f"{'Edited' if current else 'Created'} field {value.name}")
            state["existing"] = value
            self.store.select(value)

        def apply():
            commit()
            if field is None:
                state["existing"] = None
                dialog.prepare_new(next_name("Field", project.fields), [item.name for item in project.fields])
        dialog.applied.connect(apply)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            commit()
        return state["existing"]

    def edit(self, entity):
        if isinstance(entity, Material): return self._material_dialog(entity)
        from opencae.model.entities.profiles import Profile
        from opencae.model.entities.sections import Section
        if isinstance(entity, Profile): return self._profile_dialog(entity)
        if isinstance(entity, Section): return self._section_dialog(entity)
        if isinstance(entity, FieldDefinition): return self._field_dialog(entity)

    def _replace_or_append(self, attribute, old, new, description):
        project = self.store.project
        if old is None:
            self.store.add_entity(description, project.id, attribute, new)
        else:
            self.store.replace_entity(description, project.id, attribute, new)
