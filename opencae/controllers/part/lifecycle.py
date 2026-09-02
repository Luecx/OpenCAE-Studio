"""Own Part creation, duplication, geometry import, and orphan-mesh import flows."""

from __future__ import annotations

from pathlib import Path

from opencae.model.geometry import ImportedStepFeature
from opencae.model.part import Part
from opencae.model.naming import next_name
from opencae.model.core import EntityRef, clone_entity_graph
from opencae.model.entities.regions import create_region
from opencae.model.selection import (
    MeshElementOperand,
    MeshFacetOperand,
    MeshNodeOperand,
    RegionDefinition,
)
from opencae.store.commands import CompositeCommand, UpdateFieldCommand
from opencae.store.owned_collection_insert import OwnedCollectionInsertCommand
from opencae.ui.core.file_dialogs import open_file
from opencae.ui.dialogs.import_geometry import ImportGeometryDialog
from opencae.ui.dialogs.import_mesh_report import ImportMeshReportDialog
from opencae.ui.dialogs.new_part import NewPartDialog
from opencae.geometry.mesh_import import read_mesh_with_report
from opencae.geometry.cache import CACHE
from .mesh_persistence import apply_mesh_snapshot

from ..dialog_runner import get_values


class PartLifecycle:
    """Coordinate Part lifecycle operations and their persistent mutations."""

    def __init__(self, context):
        self.ctx = context

    def new_part(self, parent=None):
        values = get_values(
            NewPartDialog(
                [part.name for part in self.ctx.store.project.parts],
                parent=parent or self.ctx.parent,
                default_name=next_name("Part", self.ctx.store.project.parts),
            )
        )
        if not values:
            return
        part = Part(
            name=values["name"],
            metadata={"part_type": values["part_type"]},
        )
        self.ctx.store.add_entity(
            f"Created part {part.name}",
            self.ctx.store.project.id,
            "parts",
            part,
        )
        self.ctx.store.set_active_part(part.id)

    def duplicate_part(self):
        source = self.ctx.store.selection
        if not isinstance(source, Part):
            source = self.ctx.active_part()
        if source is None:
            self.ctx.store.message.emit("Select or activate a part first")
            return
        # Duplicating a Part intentionally performs one O(mesh-size) graph clone.
        # Transfer that already-detached clone directly into Project ownership so
        # the undo layer does not copy the same 400k-element payload again.
        clone = clone_entity_graph(source)
        clone.name = next_name(source.name, self.ctx.store.project.parts)
        self.ctx.store.execute(
            f"Duplicated part {source.name} as {clone.name}",
            OwnedCollectionInsertCommand(
                self.ctx.store.project.id,
                "parts",
                clone,
                len(self.ctx.store.project.parts),
            ),
        )
        self.ctx.store.set_active_part(clone.id)
        self.ctx.store.select(clone)
        self.ctx.store.invalidate_scene("Part duplicated")

    def edit_part(self, part):
        """Edit lightweight Part properties without cloning its potentially huge mesh."""
        values = get_values(
            NewPartDialog(
                [item.name for item in self.ctx.store.project.parts],
                part,
                self.ctx.parent,
            )
        )
        if not values:
            return
        metadata = dict(part.metadata)
        metadata["part_type"] = values["part_type"]
        commands = []
        if values["name"] != part.name:
            commands.append(
                UpdateFieldCommand(part.id, "name", part.name, values["name"])
            )
        if metadata != part.metadata:
            commands.append(
                UpdateFieldCommand(part.id, "metadata", part.metadata, metadata)
            )
        if commands:
            self.ctx.store.execute(
                f"Edited part {part.name}",
                CompositeCommand(tuple(commands)),
            )

    def import_geometry(self):
        """Import CAD geometry without cloning an existing generated mesh."""
        active = self.ctx.active_part()
        values = get_values(
            ImportGeometryDialog(
                active,
                existing_names=[p.name for p in self.ctx.store.project.parts],
                parent=self.ctx.parent,
                default_part_name=next_name(
                    "Part",
                    self.ctx.store.project.parts,
                ),
                default_feature_name=next_name(
                    "Import Geometry",
                    active.geometry if active else [],
                ),
            )
        )
        if not values:
            return

        editing_existing = bool(active and not active.geometry)
        candidate = (
            self.ctx.geometry_candidate(active)
            if editing_existing
            else Part(name=values["part_name"])
        )
        candidate.name = values["part_name"]
        candidate.geometry_settings.heal_on_import = values["heal"]
        candidate.geometry_settings.sew_faces = values["sew_faces"]
        candidate.geometry_settings.make_solids = values["make_solids"]
        candidate.geometry_settings.remove_degenerate = values["remove_degenerate"]
        candidate.geometry_settings.tolerance = values["tolerance"]
        candidate.geometry = [
            ImportedStepFeature(
                name=values["name"],
                source_file=values["file"],
            )
        ]
        if editing_existing:
            candidate.mesh.status = "Outdated"
        if not self.ctx.validate_geometry(candidate, "Import failed"):
            return

        if editing_existing:
            self.ctx.commit_geometry_candidate(
                candidate,
                f"Imported geometry into {candidate.name}",
            )
        else:
            self.ctx.store.add_entity(
                f"Imported {candidate.name}",
                self.ctx.store.project.id,
                "parts",
                candidate,
            )
            self.ctx.store.set_active_part(candidate.id)

    def import_mesh(self):
        path = open_file(
            self.ctx.parent,
            "Import Mesh",
            "Mesh files (*.inp *.fem *.vtk *.vtu *.msh);;All files (*)",
        )
        if not path:
            return
        part = Part(
            name=next_name(
                Path(path).stem or "Mesh Part",
                self.ctx.store.project.parts,
            ),
            source_type="Orphan Mesh",
            metadata={
                "part_type": "3D deformable",
                "source_file": str(path),
            },
        )
        try:
            imported = read_mesh_with_report(path, part.id)
            apply_mesh_snapshot(part, imported.snapshot)
            _apply_imported_regions(part, imported)
        except Exception as exc:
            self.ctx.error("Mesh import failed", exc)
            return
        CACHE.set_mesh(imported.snapshot)
        # The parser already built a detached Part containing the complete mesh.
        # Move that object into Project ownership; making another command copy
        # would double peak memory for large orphan meshes for no semantic gain.
        self.ctx.store.execute(
            f"Imported mesh {part.name}",
            OwnedCollectionInsertCommand(
                self.ctx.store.project.id,
                "parts",
                part,
                len(self.ctx.store.project.parts),
            ),
        )
        self.ctx.store.set_active_part(part.id)
        self.ctx.store.invalidate_scene("Mesh imported")
        if hasattr(self.ctx.parent, "viewport"):
            self.ctx.parent.viewport.set_display_mode("mesh")

        report = imported.report
        if report.has_unimported_keywords or report.warnings:
            count = len(report.not_imported)
            self.ctx.store.message.emit(
                f"Imported {part.name}; {count} keyword block(s) were not fully imported"
            )
            ImportMeshReportDialog(report, Path(path).name, self.ctx.parent).exec()

    def edit_import(self, feature):
        """Edit the source CAD feature through a geometry-only candidate."""
        candidate, target = self.ctx.feature_copy(feature)
        if target is None:
            return
        values = get_values(
            ImportGeometryDialog(
                candidate,
                target,
                [p.name for p in self.ctx.store.project.parts],
                self.ctx.parent,
            )
        )
        if not values:
            return
        candidate.name = values["part_name"]
        candidate.geometry_settings.heal_on_import = values["heal"]
        candidate.geometry_settings.sew_faces = values["sew_faces"]
        candidate.geometry_settings.make_solids = values["make_solids"]
        candidate.geometry_settings.remove_degenerate = values["remove_degenerate"]
        candidate.geometry_settings.tolerance = values["tolerance"]
        target.name = values["name"]
        target.source_file = values["file"]
        candidate.mesh.status = "Outdated"
        if self.ctx.validate_geometry(candidate, "Geometry source update failed"):
            self.ctx.commit_geometry_candidate(candidate, f"Edited {target.name}")


def _apply_imported_regions(part, imported) -> None:
    """Create object-backed Region entities for deck NSET/ELSET/SURFACE data."""
    owner_ref = EntityRef.of(part)
    revision = str(part.mesh.revision or "")
    valid_nodes = {int(value) for value in part.mesh.nodes.ids}
    valid_elements = {
        int(value)
        for block in part.mesh.element_blocks
        for value in block.ids
    }

    regions = []
    for name, node_ids in imported.node_sets.items():
        definition = RegionDefinition.from_values(
            MeshNodeOperand(
                owner_ref=owner_ref,
                node_id=node_id,
                mesh_revision=revision,
            )
            for node_id in node_ids
            if int(node_id) in valid_nodes
        )
        if not definition.empty:
            regions.append(
                create_region(
                    "Node Set",
                    name=name,
                    definition=definition,
                    geometry_backed=False,
                )
            )

    for name, element_ids in imported.element_sets.items():
        definition = RegionDefinition.from_values(
            MeshElementOperand(
                owner_ref=owner_ref,
                element_id=element_id,
                mesh_revision=revision,
            )
            for element_id in element_ids
            if int(element_id) in valid_elements
        )
        if not definition.empty:
            regions.append(
                create_region(
                    "Element Set",
                    name=name,
                    definition=definition,
                    geometry_backed=False,
                )
            )

    for name, facets in imported.surfaces.items():
        definition = RegionDefinition.from_values(
            MeshFacetOperand(
                owner_ref=owner_ref,
                element_id=element_id,
                local_face=side,
                mesh_revision=revision,
            )
            for element_id, side in facets
            if int(element_id) in valid_elements
        )
        if not definition.empty:
            regions.append(
                create_region(
                    "Surface",
                    name=name,
                    definition=definition,
                    geometry_backed=False,
                )
            )

    part.regions.extend(regions)
