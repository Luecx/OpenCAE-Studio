from __future__ import annotations

from opencae.ui.core.dialog_lifecycle import show_modeless_dialog
from PyQt6.QtWidgets import QInputDialog

from opencae.geometry.section_filter import compatible_sections
from opencae.model.core import EntityRef
from opencae.model.naming import next_name
from opencae.model.regions import CoordinateSystem, ReferencePoint, SectionAssignment, create_region
from opencae.model.selection import NamedRegionOperand, RegionProjection, region_definition_error
from opencae.ui.dialogs.coordinate_system import CoordinateSystemDialog
from opencae.ui.dialogs.element_set import ElementSetDialog
from opencae.ui.dialogs.node_set import NodeSetDialog
from opencae.ui.dialogs.reference_point import ReferencePointDialog
from opencae.ui.dialogs.section_assignment import SectionAssignmentDialog
from opencae.ui.dialogs.surface import SurfaceDialog
from ..region_selection import begin_region_pick, policy_for_projection, region_options


class PartRegions:
    def __init__(self, context):
        self.ctx = context
        self._dialogs = []

    def node_set(self): self._region(RegionProjection.NODES)
    def element_set(self): self._region(RegionProjection.ELEMENTS)
    def surface(self): self._region(RegionProjection.FACETS)

    def edit_region(self, region):
        self._region(region.preferred_projection, region)

    def _region(self, projection, region=None):
        part = self.ctx.active_part()
        if part is None: return
        project = self.ctx.store.project
        projection = RegionProjection(projection)
        dialog_cls, prefix = {
            RegionProjection.NODES: (NodeSetDialog, "NODE_REGION"),
            RegionProjection.ELEMENTS: (ElementSetDialog, "ELEMENT_REGION"),
            RegionProjection.FACETS: (SurfaceDialog, "SURFACE_REGION"),
        }[projection]
        policy = policy_for_projection(projection)
        options = _without_region(region_options(project, owner=part, projections=(projection,)), getattr(region, "id", None))

        def pick(_owner, done, finished):
            return begin_region_pick(project, self.ctx.parent.viewport, policy, done, default_owner=part, finished=finished)

        def validate(definition):
            return region_definition_error(
                project, definition, policy.requirement, allow_part_local=True
            )

        dialog = dialog_cls(
            region=region,
            project=project,
            options=options,
            pick_callback=pick,
            validator=validate,
            requirement=policy.requirement,
            allow_part_local=True,
            default_name=next_name(prefix, part.regions),
            existing_names=[item.name for item in part.regions],
            parent=self.ctx.parent,
        )
        self._dialogs.append(dialog)
        existing_id = getattr(region, "id", None)

        def commit(values):
            payload = dict(values)
            if existing_id: payload["id"] = existing_id
            replacement = create_region("Region", scope="Part", preferred_projection=projection, **payload)
            description = f"{'Edited' if existing_id else 'Created'} {replacement.name}"
            if existing_id:
                self.ctx.store.replace_entity(description, part.id, "regions", replacement)
            else:
                self.ctx.store.add_entity(description, part.id, "regions", replacement)
            self.ctx.store.select(replacement)

        preview_channel = f"part-region-dialog-{id(dialog)}"

        def preview(definition):
            self.ctx.parent.viewport.suspend_model_selection_preview()
            self.ctx.parent.viewport.show_region_preview(
                preview_channel, definition, color="#3296e6",
                opacity=.62, point_size=17, show_point_labels=True,
            )

        def finish(_code):
            self.ctx.parent.viewport.clear_region_preview(preview_channel)
            self.ctx.parent.viewport.restore_model_selection_preview()
            self._finish_dialog(dialog)

        dialog.region.value_changed.connect(preview)
        dialog.committed.connect(commit)
        dialog.finished.connect(finish)
        show_modeless_dialog(dialog)
        dialog.begin_selection()
        preview(dialog.region.definition())

    def coordinate_system(self):
        part = self.ctx.active_part()
        if part is None:
            return
        dialog = CoordinateSystemDialog(
            next_name("CSYS", part.coordinate_systems),
            [item.name for item in part.coordinate_systems],
            self.ctx.parent,
        )
        state = {"id": None}
        self._dialogs.append(dialog)
        dialog.pick_requested.connect(
            lambda allowed, callback, finished: self.ctx.parent.viewport.begin_datum_reference_pick(
                allowed, callback, finished
            )
        )
        dialog.cancel_pick_requested.connect(self.ctx.parent.viewport.cancel_context_pick)

        def commit(values):
            system = CoordinateSystem(
                id=state["id"] or None,
                name=values["name"], system_type=values["system_type"],
                origin=values["origin"], axis_1=values["axis_1"], axis_2=values["axis_2"],
                scope="Part",
            ) if state["id"] else CoordinateSystem(
                name=values["name"], system_type=values["system_type"],
                origin=values["origin"], axis_1=values["axis_1"], axis_2=values["axis_2"],
                scope="Part",
            )
            if state["id"]:
                self.ctx.store.replace_entity(f"Updated {system.name}", part.id, "coordinate_systems", system)
            else:
                self.ctx.store.add_entity(f"Created {system.name}", part.id, "coordinate_systems", system)
                state["id"] = system.id
            self.ctx.store.select(system)
            self.ctx.store.invalidate_scene("Coordinate system changed")

        dialog.apply_requested.connect(commit)
        dialog.finished.connect(lambda _code: self._finish_dialog(dialog))
        show_modeless_dialog(dialog)

    def reference_point(self):
        part = self.ctx.active_part()
        if part is None:
            return
        dialog = ReferencePointDialog(
            next_name("RP", part.reference_points),
            [item.name for item in part.reference_points],
            parent=self.ctx.parent,
        )
        state = {"id": None}
        self._dialogs.append(dialog)
        dialog.pick_requested.connect(
            lambda allowed, callback, finished: self.ctx.parent.viewport.begin_datum_reference_pick(
                allowed, callback, finished
            )
        )
        dialog.cancel_pick_requested.connect(self.ctx.parent.viewport.cancel_context_pick)

        def commit(values):
            point = ReferencePoint(
                id=state["id"] or None, name=values["name"],
                position=values["position"], scope="Part",
            ) if state["id"] else ReferencePoint(
                name=values["name"], position=values["position"], scope="Part",
            )
            if state["id"]:
                self.ctx.store.replace_entity(f"Updated {point.name}", part.id, "reference_points", point)
            else:
                self.ctx.store.add_entity(f"Created {point.name}", part.id, "reference_points", point)
                state["id"] = point.id
            self.ctx.store.select(point)
            self.ctx.store.invalidate_scene("Reference point changed")

        dialog.apply_requested.connect(commit)
        dialog.finished.connect(lambda _code: self._finish_dialog(dialog))
        show_modeless_dialog(dialog)

    def section_assignment(self, assignment=None):
        part = self.ctx.active_part()
        if part is None: return
        project = self.ctx.store.project
        resources = getattr(self.ctx.parent.controllers, "resources", None)
        def create_section(owner, done): done(resources._section_dialog(parent=owner))
        if resources is None: create_section = None
        policy = policy_for_projection(RegionProjection.ELEMENTS)

        def pick(_owner, done, finished):
            return begin_region_pick(project, self.ctx.parent.viewport, policy, done, default_owner=part, finished=finished)

        def save(_widget, definition):
            name, ok = QInputDialog.getText(self.ctx.parent, "Save Region", "Region name:", text=next_name("ELEMENT_REGION", part.regions))
            if not ok or not name.strip(): return
            region = create_region("Region", name=name.strip(), scope="Part", definition=definition, preferred_projection=RegionProjection.ELEMENTS)
            self.ctx.store.add_entity(f"Created {region.name}", part.id, "regions", region)

        def validate(definition):
            return region_definition_error(
                project, definition, policy.requirement, allow_part_local=True
            )

        dialog = SectionAssignmentDialog(
            project=project,
            sections=project.sections,
            regions=region_options(project, owner=part, include_reference_points=False, projections=(RegionProjection.ELEMENTS,)),
            orientations=part.orientations,
            create_section=create_section,
            create_region=save,
            pick_region=pick,
            default_name=next_name("Section Assignment", part.section_assignments),
            existing_names=[item.name for item in part.section_assignments],
            assignment=assignment,
            section_filter=lambda definition: compatible_sections(project, part, definition),
            target_validator=validate,
            target_requirement=policy.requirement,
            parent=self.ctx.parent,
        )
        self._dialogs.append(dialog)
        state = {"existing_id": getattr(assignment, "id", None)}
        preview_channel = f"section-assignment-dialog-{id(dialog)}"

        def preview(definition):
            self.ctx.parent.viewport.show_region_preview(
                preview_channel, definition, color="#3296e6",
                opacity=.62, point_size=16, show_point_labels=False,
            )

        def finish(_code):
            self.ctx.parent.viewport.clear_region_preview(preview_channel)
            self._finish_dialog(dialog)

        dialog.target.value_changed.connect(preview)
        dialog.applied.connect(lambda: state.update(existing_id=self._commit_assignment(part.id, dialog, state["existing_id"])))
        dialog.accepted.connect(lambda: state.update(existing_id=self._commit_assignment(part.id, dialog, state["existing_id"])))
        dialog.finished.connect(finish)
        show_modeless_dialog(dialog)
        preview(dialog.target.definition())

    def edit_assignment(self, assignment): self.section_assignment(assignment)

    def _commit_assignment(self, part_id, dialog, existing_id=None):
        values = dialog.values()
        if existing_id: values["id"] = existing_id
        assignment = SectionAssignment(**values)
        description = f"{'Edited' if existing_id else 'Created'} {assignment.name}"
        if existing_id:
            self.ctx.store.replace_entity(description, part_id, "section_assignments", assignment)
        else:
            self.ctx.store.add_entity(description, part_id, "section_assignments", assignment)
        self.ctx.store.select(assignment)
        return assignment.id

    def _finish_dialog(self, dialog):
        if hasattr(self.ctx.parent, "viewport"):
            self.ctx.parent.viewport.cancel_context_pick()
        if dialog in self._dialogs:
            self._dialogs.remove(dialog)


def _without_region(options, region_id):
    if not region_id: return options
    result = []
    for label, definition in options:
        if any(isinstance(item.operand, NamedRegionOperand) and item.operand.region_ref.entity_id == region_id for item in definition.items):
            continue
        result.append((label, definition))
    return result
