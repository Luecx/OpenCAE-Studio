from PyQt6.QtWidgets import QDialog

from opencae.model.naming import next_name
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

    def _selection_labels(self): return self.ctx.selected_labels()
    def node_set(self): self._region(NodeSetDialog, "node_sets", "Node Set", "NODE_SET")
    def element_set(self): self._region(ElementSetDialog, "element_sets", "Element Set", "ELEMENT_SET")
    def surface(self): self._region(SurfaceDialog, "surfaces", "Surface", "SURFACE")

    def _region(self, dialog_cls, target, region_type, prefix, region=None):
        part = self.ctx.active_part()
        if part is None: return
        collection = getattr(part, target)
        dialog = dialog_cls(region, self._selection_labels, next_name(prefix, collection),
                            [item.name for item in collection], self.ctx.parent)
        self._session.open(dialog, lambda values: self._commit(part.id, target, region_type, region, values))

    def _commit(self, part_id, target, region_type, region, values):
        part = next((item for item in self.ctx.store.project.parts if item.id == part_id), None)
        if part is None: return
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

    def section_assignment(self):
        part = self.ctx.active_part()
        if part is None: return
        project = self.ctx.store.project; regions = [r.name for r in (*part.element_sets, *part.surfaces)]
        resources = getattr(self.ctx.parent.controllers, "resources", None)
        create_section = (lambda owner=None: resources._section_dialog(parent=owner)) if resources else None
        dialog = SectionAssignmentDialog([s.name for s in project.sections], regions, [o.name for o in part.orientations], create_section,
            lambda owner, done: self._nested_element_set(part, owner, done), next_name("Section Assignment", part.section_assignments),
            [item.name for item in part.section_assignments], parent=self.ctx.parent)
        dialog.setModal(False); self._dialogs.append(dialog)
        dialog.accepted.connect(lambda: self._commit_assignment(part, dialog))
        dialog.finished.connect(lambda _code: self._dialogs.remove(dialog) if dialog in self._dialogs else None)
        dialog.show(); dialog.raise_(); dialog.activateWindow()

    def _commit_assignment(self, part, dialog):
        assignment = SectionAssignment(**dialog.values())
        self.ctx.store.mutate(f"Created {assignment.name}", lambda p: part.section_assignments.append(assignment))

    def _nested_element_set(self, part, owner, done):
        owner.hide(); collection = part.element_sets
        dialog = ElementSetDialog(selection_provider=self._selection_labels, default_name=next_name("ELEMENT_SET", collection), existing_names=[i.name for i in collection], parent=self.ctx.parent)
        open_nested_region(self.ctx, dialog, owner, lambda values: self._finish_nested(part, values, done))

    def _finish_nested(self, part, values, done):
        value = create_region("Element Set", **values)
        self.ctx.store.mutate(f"Created {value.name}", lambda _project: part.element_sets.append(value)); done(value.name)
