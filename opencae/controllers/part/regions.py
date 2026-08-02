from PyQt6.QtWidgets import QDialog

from opencae.model.naming import next_name
from opencae.model.core import members_from_selection, region_member_label
from opencae.geometry.section_filter import compatible_sections
from opencae.model.regions import CoordinateSystem, ReferencePoint, SectionAssignment, create_region
from opencae.ui.dialogs.coordinate_system import CoordinateSystemDialog
from opencae.ui.dialogs.element_set import ElementSetDialog
from opencae.ui.dialogs.node_set import NodeSetDialog
from opencae.ui.dialogs.reference_point import ReferencePointDialog
from opencae.ui.dialogs.section_assignment import SectionAssignmentDialog
from opencae.ui.dialogs.surface import SurfaceDialog

from ..dialog_runner import get_values
from ..region_dialog_session import RegionDialogSession
from ..region_nested import open_nested_region


class PartRegions:
    def __init__(self, context):
        self.ctx = context; self._dialogs = []
        self._session = RegionDialogSession(context.store, context.parent, self._dialogs)

    def _selection_labels(self): return members_from_selection(self.ctx.store.project, self.ctx.store.selection, self.ctx.active_part())
    def node_set(self): self._region(NodeSetDialog, "node_sets", "Node Set", "NODE_SET")
    def element_set(self): self._region(ElementSetDialog, "element_sets", "Element Set", "ELEMENT_SET")
    def surface(self): self._region(SurfaceDialog, "surfaces", "Surface", "SURFACE")

    def _region(self, dialog_cls, target, region_type, prefix, region=None):
        part = self.ctx.active_part()
        if part is None: return
        collection = getattr(part, target)
        dialog = dialog_cls(region, self._selection_labels, next_name(prefix, collection),
                            [item.name for item in collection], self.ctx.parent,
                            lambda member: region_member_label(self.ctx.store.project, member))
        self._session.open(dialog, lambda values: self._commit(part.id, target, region_type, region, values))

    def _commit(self, part_id, target, region_type, region, values):
        part = next((item for item in self.ctx.store.project.parts if item.id == part_id), None)
        if part is None: return
        if region is not None: values["id"] = region.id
        value = create_region(region_type, **values)
        def apply(_project):
            collection = getattr(part, target)
            if region is None: collection.append(value)
            else: collection[collection.index(region)] = value
        self.ctx.store.mutate(f"{'Edited' if region else 'Created'} {value.name}", apply)

    def edit_region(self, region):
        part = self.ctx.active_part()
        specs = (("node_sets", "Node Set", "NODE_SET", NodeSetDialog),
                 ("element_sets", "Element Set", "ELEMENT_SET", ElementSetDialog),
                 ("surfaces", "Surface", "SURFACE", SurfaceDialog))
        for target, kind, prefix, dialog in specs:
            if part and region in getattr(part, target): return self._region(dialog, target, kind, prefix, region)

    def coordinate_system(self):
        part = self.ctx.active_part()
        if part is None: return
        values = get_values(CoordinateSystemDialog(next_name("CSYS", part.coordinate_systems),
                                                    [item.name for item in part.coordinate_systems], self.ctx.parent))
        if values:
            csys = CoordinateSystem(name=values["name"], system_type=values["system_type"], origin=values["origin"], axis_1=values["axis_1"], axis_2=values["axis_2"], scope="Part")
            self.ctx.store.mutate(f"Created {csys.name}", lambda p: part.coordinate_systems.append(csys)); self.ctx.store.invalidate_scene("Coordinate system created")

    def reference_point(self):
        part = self.ctx.active_part()
        if part is None: return
        values = get_values(ReferencePointDialog(next_name("RP", part.reference_points),
                                                  [item.name for item in part.reference_points], parent=self.ctx.parent))
        if values:
            point = ReferencePoint(name=values["name"], position=(values["x"], values["y"], values["z"]))
            self.ctx.store.mutate(f"Created {point.name}", lambda p: part.reference_points.append(point))

    def section_assignment(self, assignment=None):
        part=self.ctx.active_part()
        if part is None:return
        project=self.ctx.store.project; resources=getattr(self.ctx.parent.controllers,"resources",None); create_section=(lambda owner=None:resources._section_dialog(parent=owner)) if resources else None
        dialog=SectionAssignmentDialog(
            sections=project.sections,regions=part.element_sets,orientations=part.orientations,create_section=create_section,
            create_region=lambda owner,done:self._nested_element_set(part,owner,done),pick_region=None,
            default_name=next_name("Section Assignment",part.section_assignments),existing_names=[item.name for item in part.section_assignments],
            assignment=assignment,section_filter=lambda region_id:compatible_sections(project,part,region_id),parent=self.ctx.parent)
        dialog.setModal(False);self._dialogs.append(dialog);state={"existing":assignment}
        def commit():state["existing"]=self._commit_assignment(part.id,dialog,state["existing"])
        dialog.applied.connect(commit);dialog.accepted.connect(commit);dialog.finished.connect(lambda _code:self._finish_dialog(dialog));dialog.show();dialog.raise_();dialog.activateWindow()


    def _finish_dialog(self, dialog):
        self.ctx.parent.viewport.cancel_context_pick()
        if dialog in self._dialogs:
            self._dialogs.remove(dialog)

    def edit_assignment(self,assignment):self.section_assignment(assignment)

    def _commit_assignment(self,part_id,dialog,old=None):
        values=dialog.values()
        if old:values["id"]=old.id
        assignment=SectionAssignment(**values)
        def apply(project):
            part=project.try_resolve(part_id); collection=part.section_assignments
            if old is None:collection.append(assignment)
            else:
                index=next(i for i,item in enumerate(collection) if item.id==old.id);collection[index]=assignment
        self.ctx.store.mutate(f"{'Edited' if old else 'Created'} {assignment.name}",apply);self.ctx.store.select(assignment);return assignment

    def _nested_element_set(self, part, owner, done):
        owner.hide(); collection = part.element_sets
        dialog = ElementSetDialog(selection_provider=self._selection_labels, default_name=next_name("ELEMENT_SET", collection), existing_names=[i.name for i in collection], parent=self.ctx.parent, member_formatter=lambda member: region_member_label(self.ctx.store.project, member))
        open_nested_region(self.ctx, dialog, owner, lambda values: self._finish_nested(part, values, done))

    def _finish_nested(self, part, values, done):
        value = create_region("Element Set", **values)
        self.ctx.store.mutate(f"Created {value.name}", lambda _project: part.element_sets.append(value)); done(value)
