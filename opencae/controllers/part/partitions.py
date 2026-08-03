from __future__ import annotations

from copy import deepcopy

from opencae.model.datums import create_datum
from opencae.model.entities.datums import DatumPlane
from opencae.model.geometry import GeometryFeature, ImportedStepFeature, PartitionEdgeFeature, PartitionFaceFeature, PartitionPlaneFeature
from opencae.model.core import EntityRef
from opencae.model.naming import next_name
from opencae.model.selection import (
    RegionProjection, RegionRequirement, SelectableKind, SelectionPolicy,
)
from opencae.ui.core.dialog_lifecycle import show_modeless_dialog
from opencae.ui.dialogs.datum_plane import DatumPlaneDialog
from opencae.ui.dialogs.partition import PartitionDialog

from ..region_selection import begin_region_pick, region_options


_DIMENSION_KIND = {
    0: SelectableKind.GEOMETRY_VERTEX,
    1: SelectableKind.GEOMETRY_EDGE,
    2: SelectableKind.GEOMETRY_FACE,
    3: SelectableKind.GEOMETRY_CELL,
}


class PartPartitions:
    def __init__(self, context):
        self.ctx = context
        self._dialogs = []

    def partition(self):
        part = self.ctx.active_part()
        if self.ctx.require_geometry(part): self._open_dialog(part)

    def edit_partition(self, feature):
        part = self.ctx.active_part()
        if part: self._open_dialog(part, feature)

    def _open_dialog(self, part, feature=None):
        project = self.ctx.store.project
        datum_planes = [item for item in part.datums if isinstance(item, DatumPlane)]

        def pick(dimension, _owner, done, finished):
            if dimension == "datum_plane":
                policy = SelectionPolicy.create({SelectableKind.DATUM_PLANE}, multiple=False)

                def selected(hit):
                    plane = self.ctx.store.project.try_resolve(hit.entity_id) if hit.entity_id else None
                    if isinstance(plane, DatumPlane):
                        done(plane)
                    else:
                        self.ctx.parent.viewport.message.emit("The selected datum plane no longer exists")

                return self.ctx.parent.viewport.begin_selection_session(policy, selected, finished=finished)

            dimension = int(dimension)
            projection = {
                0: RegionProjection.NODES,
                1: RegionProjection.ELEMENTS,
                2: RegionProjection.FACETS,
                3: RegionProjection.ELEMENTS,
            }[dimension]
            policy = SelectionPolicy.create(
                {_DIMENSION_KIND[dimension]},
                multiple=False,
                requirement=RegionRequirement(projection, (dimension,), 1),
            )
            return begin_region_pick(project, self.ctx.parent.viewport, policy, done, default_owner=part, finished=finished)

        dialog = PartitionDialog(
            project,
            part,
            self.ctx.selected_points,
            feature,
            self.ctx.parent,
            region_options=region_options(project, owner=part, include_reference_points=False),
            pick_callback=pick,
            datum_planes=datum_planes,
            create_datum_plane=lambda owner, done, pid=part.id: self._create_datum_plane(pid, owner, done),
        )
        self._dialogs.append(dialog)
        state = {"feature_id": getattr(feature, "id", None)}
        preview_prefix = f"partition-dialog-{id(dialog)}"

        def active_selectors():
            index = dialog.stack.currentIndex()
            if index == 0:
                return (dialog.plane_targets,)
            if index == 1:
                return (dialog.face_targets,)
            if index == 2:
                return (dialog.edge_parameter_targets,)
            return (dialog.edge_vertex_targets, dialog.edge_vertex)

        def preview(*_):
            viewport = self.ctx.parent.viewport
            viewport.clear_region_previews(preview_prefix)
            for index, selector in enumerate(active_selectors()):
                viewport.show_region_preview(
                    f"{preview_prefix}-{index}", selector.definition(),
                    color="#3296e6", opacity=.62, point_size=17,
                    show_point_labels=True,
                )

        for selector in (
            dialog.plane_targets, dialog.face_targets,
            dialog.edge_parameter_targets, dialog.edge_vertex_targets,
            dialog.edge_vertex,
        ):
            selector.value_changed.connect(preview)
        dialog.stack.currentChanged.connect(preview)
        dialog.committed.connect(lambda values, pid=part.id, s=state: s.update(feature_id=self._apply(values, pid, s["feature_id"])))
        dialog.finished.connect(lambda _code, d=dialog, prefix=preview_prefix: self._finish_dialog(d, prefix))
        show_modeless_dialog(dialog)
        preview()

    def _finish_dialog(self, dialog, preview_prefix=None):
        if hasattr(self.ctx.parent, "viewport"):
            self.ctx.parent.viewport.cancel_context_pick()
            if preview_prefix:
                self.ctx.parent.viewport.clear_region_previews(preview_prefix)
        if dialog in self._dialogs: self._dialogs.remove(dialog)

    def _apply(self, values, part_id, feature_id):
        part = self.ctx.store.project.try_resolve(part_id)
        if part is None: return feature_id
        candidate = deepcopy(part)
        existing_index = next((index for index, item in enumerate(candidate.geometry) if item.id == feature_id), None)
        existing = candidate.geometry[existing_index] if existing_index is not None else None
        cls = {
            "Cell by plane": PartitionPlaneFeature,
            "Face by two points": PartitionFaceFeature,
            "Edge at parameter": PartitionEdgeFeature,
            "Edge at vertex": PartitionEdgeFeature,
        }[values["partition_type"]]
        kwargs = {"name": values["name"], "target": values["target"]}
        feature_values = values["values"]
        if cls is PartitionPlaneFeature:
            datum_id = str(feature_values.get("datum_plane_id") or "")
            datum = next((item for item in part.datums if isinstance(item, DatumPlane) and item.id == datum_id), None)
            if datum is None:
                self.ctx.store.message.emit("Select an existing datum plane for the partition")
                return feature_id
            kwargs.update(
                origin=tuple(datum.origin), normal=tuple(datum.normal),
                datum_plane_ref=EntityRef(datum.id, "DatumPlane"),
            )
        elif cls is PartitionFaceFeature:
            kwargs["points"] = tuple(feature_values["points"])
        else:
            kwargs.update(
                method=feature_values["method"], fraction=feature_values.get("fraction", 0.5),
                split_target=values["split_target"],
            )
        if existing is not None: kwargs["id"] = existing.id
        replacement = cls(**kwargs)
        if existing is None:
            candidate.geometry.append(replacement)
        else:
            replacement.suppressed = existing.suppressed
            candidate.geometry[existing_index] = replacement
        candidate.mesh.status = "Outdated"
        if self.ctx.validate_geometry(candidate, "Partition failed"):
            self.ctx.replace_part(candidate, f"{'Edited' if existing else 'Created'} {replacement.name}")
            return replacement.id
        return feature_id

    def _create_datum_plane(self, part_id, owner, done):
        part = self.ctx.store.project.try_resolve(part_id)
        if part is None: return
        dialog = DatumPlaneDialog(next_name("Datum Plane", part.datums), [item.name for item in part.datums], part.coordinate_systems, owner or self.ctx.parent)
        dialog.pick_requested.connect(lambda allowed, callback, finished: self.ctx.parent.viewport.begin_datum_reference_pick(allowed, callback, finished))
        dialog.cancel_pick_requested.connect(self.ctx.parent.viewport.cancel_context_pick)
        dialog.preview_requested.connect(self.ctx.parent.viewport.show_datum_preview)

        def apply(values):
            current = self.ctx.store.project.try_resolve(part_id)
            if current is None: return
            datum = create_datum(values["kind"], values["name"], values["method"], values["parameters"])
            self.ctx.store.add_entity(f"Created {datum.name}", current.id, "datums", datum)
            stored = self.ctx.store.project.try_resolve(datum.id)
            if stored is not None: self.ctx.store.select(stored)
            self.ctx.store.invalidate_scene("Datum updated")
            done(stored or datum)
            dialog.close()

        dialog.apply_requested.connect(apply)
        dialog.finished.connect(lambda _code: (self.ctx.parent.viewport.cancel_context_pick(), self.ctx.parent.viewport.hide_datum_preview()))
        show_modeless_dialog(dialog)

    def rebuild_geometry(self):
        part = self.ctx.active_part()
        if self.ctx.require_geometry(part) and self.ctx.validate_geometry(deepcopy(part), "Geometry rebuild failed"):
            self.ctx.store.invalidate_scene(f"Rebuilt geometry for {part.name}")
            self.ctx.store.message.emit(f"Rebuilt geometry for {part.name}")

    def suppress_feature(self):
        part = self.ctx.active_part(); selected = self.ctx.store.selection
        feature = selected if isinstance(selected, GeometryFeature) else None
        if feature is None and part:
            feature = next((item for item in reversed(part.geometry) if not isinstance(item, ImportedStepFeature)), None)
        if part is None or feature is None:
            self.ctx.store.message.emit("Select a partition feature first"); return
        if isinstance(feature, ImportedStepFeature):
            self.ctx.store.message.emit("The source geometry feature cannot be suppressed"); return
        candidate, target = self.ctx.feature_copy(feature)
        target.suppressed = not target.suppressed; candidate.mesh.status = "Outdated"
        if self.ctx.validate_geometry(candidate, "Feature update failed"):
            self.ctx.replace_part(candidate, f"{'Resumed' if not target.suppressed else 'Suppressed'} {target.name}")
