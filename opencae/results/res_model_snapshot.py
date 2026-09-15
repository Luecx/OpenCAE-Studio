"""Rebuild result topology from the OpenCAE snapshot paired with a FEMaster RES."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from opencae.persistence.project_io import load_project
from opencae.solvers.femaster_dsl.element_types import element_type

_VTK_TYPES = {
    "T3": 3,
    "B33": 3,
    "S3": 5,
    "MITC3FRT": 5,
    "S4": 9,
    "MITC4": 9,
    "MITC4FRT": 9,
    "QSPT": 9,
    "S6": 22,
    "MITC6FRT": 22,
    "S8": 23,
    "MITC8": 23,
    "MITC8FRT": 23,
    "C3D4": 10,
    "C3D5": 14,
    "C3D6": 13,
    "C3D8": 12,
    "C3D8R": 12,
    "C3D10": 24,
    "C3D13": 27,
    "C3D15": 26,
    "C3D20": 25,
    "C3D20R": 25,
}


@dataclass(frozen=True, slots=True)
class ResultModel:
    project: object
    points: np.ndarray
    node_ids: np.ndarray
    node_keys: tuple[str, ...]
    cells: np.ndarray
    celltypes: np.ndarray
    element_ids: np.ndarray
    element_keys: tuple[str, ...]


def resolve_model_path(result_path: str | Path) -> Path:
    """Return the same-stem OCAE snapshot required by a standalone RES file."""
    source = Path(result_path)
    snapshot = source.with_suffix(".ocae")
    if not snapshot.is_file():
        raise FileNotFoundError(
            "FEMaster RES results require the OpenCAE model snapshot saved with "
            f"the run. Expected '{snapshot.name}' beside '{source.name}'."
        )
    return snapshot


def load_result_model(result_path: str | Path) -> ResultModel:
    snapshot = resolve_model_path(result_path)
    return build_result_model(load_project(snapshot))


def build_result_model(project) -> ResultModel:
    """Reproduce the global node/element ordering used by the FEMaster exporter."""
    points: list[tuple[float, float, float]] = []
    node_ids: list[int] = []
    node_keys: list[str] = []
    cells: list[int] = []
    celltypes: list[int] = []
    element_ids: list[int] = []
    element_keys: list[str] = []

    node_offset = 0
    element_offset = 0
    instances = tuple(
        instance for instance in project.assembly.instances if not instance.suppressed
    )
    if not instances:
        raise ValueError("OpenCAE result snapshot has no active assembly instances")

    for instance in instances:
        part = project.try_resolve(instance.part_ref)
        if part is None:
            raise ValueError(f"Instance '{instance.name}' references a missing Part")
        rotation = _rotation(instance.rotation)
        translation = np.asarray(instance.translation, dtype=float)
        point_for_local: dict[int, int] = {}

        for index, (local_id, coordinates) in enumerate(
            zip(part.mesh.nodes.ids, part.mesh.nodes.coordinates, strict=True), 1
        ):
            global_id = node_offset + index
            point_for_local[int(local_id)] = len(points)
            point = rotation @ np.asarray(coordinates, dtype=float) + translation
            points.append(tuple(float(value) for value in point))
            node_ids.append(global_id)
            node_keys.append(f"{instance.name}.{int(local_id)}")
        node_offset += len(part.mesh.nodes.ids)

        for reference in part.reference_points:
            node_offset += 1
            point = rotation @ np.asarray(reference.position, dtype=float) + translation
            points.append(tuple(float(value) for value in point))
            node_ids.append(node_offset)
            node_keys.append(f"{instance.name}.{node_offset}")

        for block in part.mesh.element_blocks:
            if not block.connectivity:
                continue
            solver_type = element_type(block.definition, len(block.connectivity[0]))
            if solver_type is None:
                continue
            vtk_type = _VTK_TYPES.get(str(solver_type).upper())
            for local_id, connectivity in zip(block.ids, block.connectivity, strict=True):
                element_offset += 1
                if vtk_type is None:
                    continue
                try:
                    indices = tuple(point_for_local[int(node)] for node in connectivity)
                except KeyError as exc:
                    raise ValueError(
                        f"Exported element {element_offset} references missing node "
                        f"{int(exc.args[0])}"
                    ) from exc
                cells.extend((len(indices), *indices))
                celltypes.append(vtk_type)
                element_ids.append(element_offset)
                element_keys.append(f"{instance.name}.{int(local_id)}")

    for reference in project.assembly.reference_points:
        node_offset += 1
        points.append(tuple(float(value) for value in reference.position))
        node_ids.append(node_offset)
        node_keys.append(str(node_offset))

    if not points:
        raise ValueError("OpenCAE result snapshot contains no exported nodes")
    if not cells:
        raise ValueError("OpenCAE result snapshot contains no renderable finite elements")

    return ResultModel(
        project=project,
        points=np.asarray(points, dtype=float),
        node_ids=np.asarray(node_ids, dtype=np.int64),
        node_keys=tuple(node_keys),
        cells=np.asarray(cells, dtype=np.int64),
        celltypes=np.asarray(celltypes, dtype=np.uint8),
        element_ids=np.asarray(element_ids, dtype=np.int64),
        element_keys=tuple(element_keys),
    )


def _rotation(rotation) -> np.ndarray:
    angles = np.radians(np.asarray(rotation, dtype=float))
    cx, cy, cz = np.cos(angles)
    sx, sy, sz = np.sin(angles)
    rx = np.asarray(((1, 0, 0), (0, cx, -sx), (0, sx, cx)), dtype=float)
    ry = np.asarray(((cy, 0, sy), (0, 1, 0), (-sy, 0, cy)), dtype=float)
    rz = np.asarray(((cz, -sz, 0), (sz, cz, 0), (0, 0, 1)), dtype=float)
    return rz @ ry @ rx
