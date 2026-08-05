"""Builds the stable OpenCAE-to-FEMaster element manifest for topology runs."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

import numpy as np

from opencae.model.entities.resources.material_behaviors import DensityBehavior
from opencae.model.selection import (
    RegionDefinition,
    RegionProjection,
    RegionRequirement,
    RegionResolver,
)
from opencae.solvers.femaster_dsl.element_types import element_type


@dataclass(slots=True)
class TopologyMeshIndex:
    """Stable solver ids, source occurrences, centroids and material densities."""

    solver_ids: np.ndarray
    part_ids: tuple[str, ...]
    instance_ids: tuple[str, ...]
    source_element_ids: np.ndarray
    centroids: np.ndarray
    material_densities: np.ndarray
    fingerprint: str
    occurrence_to_row: dict[tuple[str, str, int], int]

    @property
    def count(self) -> int:
        return int(len(self.solver_ids))

    def mask_for(self, project, definition: RegionDefinition) -> np.ndarray:
        resolved = RegionResolver(project).resolve(
            RegionDefinition.from_values(definition),
            RegionRequirement(
                RegionProjection.ELEMENTS,
                allowed_dimensions=(1, 2, 3),
                min_count=1,
            ),
        )
        if not resolved.valid:
            raise ValueError(
                "; ".join(item.message for item in resolved.diagnostics)
            )
        mask = np.zeros(self.count, dtype=bool)
        for occurrence in resolved.elements:
            key = (
                occurrence.owner_id,
                occurrence.instance_id or "",
                int(occurrence.element_id),
            )
            row = self.occurrence_to_row.get(key)
            if row is not None:
                mask[row] = True
        if not np.any(mask):
            raise ValueError(
                "The selected optimization region contains no exported elements"
            )
        return mask


def build_mesh_index(project) -> TopologyMeshIndex:
    """Create the solver-element manifest for all active assembly instances."""

    instances = [
        item for item in project.assembly.instances if not item.suppressed
    ]
    if not instances:
        raise ValueError(
            "Topology optimization requires at least one active assembly instance"
        )

    solver_ids: list[int] = []
    part_ids: list[str] = []
    instance_ids: list[str] = []
    element_ids: list[int] = []
    centroids: list[np.ndarray] = []
    occurrence_to_row: dict[tuple[str, str, int], int] = {}
    next_solver_id = 1

    for instance in instances:
        part = project.try_resolve(instance.part_ref)
        if part is None:
            continue
        node_coordinates = {
            int(node_id): np.asarray(point, dtype=float)
            for node_id, point in zip(
                part.mesh.nodes.ids,
                part.mesh.nodes.coordinates,
            )
        }
        rotation, translation = _transform(instance)
        for block in part.mesh.element_blocks:
            if not block.connectivity:
                continue
            mapped = element_type(
                block.definition,
                len(block.connectivity[0]),
            )
            if mapped is None:
                continue
            for local_id, connectivity in zip(
                block.ids,
                block.connectivity,
            ):
                try:
                    local_points = np.asarray(
                        [
                            node_coordinates[int(node)]
                            for node in connectivity
                        ],
                        dtype=float,
                    )
                except KeyError as exc:
                    raise ValueError(
                        f"Element {local_id} in part {part.name} references "
                        f"missing node {exc.args[0]}"
                    ) from exc
                world_points = (
                    rotation @ local_points.T
                ).T + translation
                row = len(solver_ids)
                solver_ids.append(next_solver_id)
                part_ids.append(part.id)
                instance_ids.append(instance.id)
                element_ids.append(int(local_id))
                centroids.append(np.mean(world_points, axis=0))
                occurrence_to_row[
                    (part.id, instance.id, int(local_id))
                ] = row
                next_solver_id += 1

    if not solver_ids:
        raise ValueError(
            "The active assembly contains no FEMaster-supported mesh elements"
        )

    solver_array = np.asarray(solver_ids, dtype=np.int64)
    element_array = np.asarray(element_ids, dtype=np.int64)
    centroid_array = np.asarray(centroids, dtype=float)
    material_densities = _material_densities(
        project,
        part_ids,
        instance_ids,
        element_array,
        occurrence_to_row,
    )
    fingerprint = _fingerprint(
        solver_array,
        part_ids,
        instance_ids,
        element_array,
        centroid_array,
    )
    return TopologyMeshIndex(
        solver_array,
        tuple(part_ids),
        tuple(instance_ids),
        element_array,
        centroid_array,
        material_densities,
        fingerprint,
        occurrence_to_row,
    )


def _material_densities(
    project,
    part_ids,
    instance_ids,
    element_ids,
    occurrence_to_row,
):
    result = np.full(len(element_ids), np.nan, dtype=float)
    requirement = RegionRequirement(
        RegionProjection.ELEMENTS,
        allowed_dimensions=(1, 2, 3),
        min_count=1,
    )
    resolver = RegionResolver(project)
    seen_occurrences = sorted(set(zip(part_ids, instance_ids)))
    for part_id, instance_id in seen_occurrences:
        part = project.try_resolve(part_id)
        if part is None:
            continue
        for assignment in part.section_assignments:
            section = project.try_resolve(assignment.section_ref)
            material = (
                project.try_resolve(getattr(section, "material_ref", None))
                if section
                else None
            )
            density = _material_density(material)
            if density is None:
                continue
            resolved = resolver.resolve(
                assignment.target,
                requirement,
                instance_id=instance_id,
                allow_part_local=True,
            )
            if not resolved.valid:
                continue
            for occurrence in resolved.elements:
                key = (
                    occurrence.owner_id,
                    occurrence.instance_id or instance_id,
                    int(occurrence.element_id),
                )
                row = occurrence_to_row.get(key)
                if row is not None:
                    result[row] = density
    return result


def _material_density(material) -> float | None:
    if material is None:
        return None
    for behavior in getattr(material, "behaviors", ()):
        if isinstance(behavior, DensityBehavior):
            value = float(behavior.value)
            return value if value > 0.0 else None
    value = float(getattr(material, "density", 0.0) or 0.0)
    return value if value > 0.0 else None


def _transform(instance):
    angles = np.radians(np.asarray(instance.rotation, dtype=float))
    cx, cy, cz = np.cos(angles)
    sx, sy, sz = np.sin(angles)
    rx = np.asarray(
        ((1, 0, 0), (0, cx, -sx), (0, sx, cx)),
        dtype=float,
    )
    ry = np.asarray(
        ((cy, 0, sy), (0, 1, 0), (-sy, 0, cy)),
        dtype=float,
    )
    rz = np.asarray(
        ((cz, -sz, 0), (sz, cz, 0), (0, 0, 1)),
        dtype=float,
    )
    return rz @ ry @ rx, np.asarray(instance.translation, dtype=float)


def _fingerprint(
    solver_ids,
    part_ids,
    instance_ids,
    element_ids,
    centroids,
) -> str:
    digest = sha256()
    digest.update(np.asarray(solver_ids, dtype=np.int64).tobytes())
    digest.update(np.asarray(element_ids, dtype=np.int64).tobytes())
    digest.update(np.asarray(centroids, dtype=np.float64).tobytes())
    for value in (*part_ids, *instance_ids):
        digest.update(str(value).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()
