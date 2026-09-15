"""Build and apply hexahedral visualization volumes for beam elements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np

from opencae.model.entities.profiles.section_geometry import section_patches
from .beam_physical_model import BeamOccurrence, beam_occurrences
from .beam_physical_stress import (
    recover_normal_stress,
    stress_coefficients,
    stress_display_values,
)

ProgressCallback = Callable[[int, int, str], None]
_BEAM_NORMAL_STRESS = "BEAM:Normal Stress"
_VTK_HEXAHEDRON = 12


@dataclass(slots=True)
class BeamPhysicalRepresentation:
    """Cached beam volume topology and mappings for compatible source frames."""

    cells: np.ndarray
    celltypes: np.ndarray
    cell_source: np.ndarray
    source_point_count: int
    source_node_ids: np.ndarray | None
    source_element_ids: np.ndarray | None
    generated_source_a: np.ndarray
    generated_source_b: np.ndarray
    generated_xi: np.ndarray
    generated_offset: np.ndarray
    generated_stress_coefficients: np.ndarray
    generated_solver_element_ids: np.ndarray

    @property
    def generated_point_count(self) -> int:
        return int(len(self.generated_source_a))

    def expand(
        self,
        source_grid,
        selected_scalar: str | None = None,
        *,
        element_nodal_forces: dict[int, np.ndarray] | None = None,
    ):
        """Replace mapped beam lines by hexahedral visualization cells."""
        import pyvista as pv

        self._validate(source_grid)
        grid = pv.UnstructuredGrid(self.cells, self.celltypes, self._points(source_grid))
        self._map_point_data(source_grid, grid)
        self._map_cell_data(source_grid, grid)
        self._attach_mapping(source_grid, grid)

        stress = recover_normal_stress(
            source_grid,
            self.generated_source_a,
            self.generated_source_b,
            self.generated_xi,
            self.generated_stress_coefficients,
            solver_element_ids=self.generated_solver_element_ids,
            element_nodal_forces=element_nodal_forces,
        )
        if stress is not None:
            values = np.full(grid.n_points, np.nan, dtype=float)
            values[self.source_point_count :] = stress
            grid.point_data[_BEAM_NORMAL_STRESS] = values
            if _is_stress_scalar(selected_scalar):
                displayed = (
                    np.asarray(grid.point_data[selected_scalar], dtype=float).copy()
                    if selected_scalar in grid.point_data
                    else np.full(grid.n_points, np.nan, dtype=float)
                )
                displayed[self.source_point_count :] = stress_display_values(
                    selected_scalar,
                    stress,
                )
                grid.point_data[selected_scalar] = displayed
        try:
            grid.set_active_scalars(None)
        except (AttributeError, KeyError, TypeError, ValueError):
            pass
        return grid

    def _points(self, source_grid) -> np.ndarray:
        source_points = np.asarray(source_grid.points, dtype=float)
        a = source_points[self.generated_source_a]
        b = source_points[self.generated_source_b]
        xi = self.generated_xi[:, None]
        centers = (1.0 - xi) * a + xi * b
        return np.vstack((source_points, centers + self.generated_offset))

    def _map_point_data(self, source_grid, target) -> None:
        a = self.generated_source_a
        b = self.generated_source_b
        xi = self.generated_xi
        for key in source_grid.point_data.keys():
            values = np.asarray(source_grid.point_data[key])
            if len(values) != self.source_point_count:
                continue
            try:
                generated = _interpolate(values, a, b, xi)
            except (TypeError, ValueError):
                continue
            if str(key) == "node_id":
                generated = np.full(len(a), -1, dtype=values.dtype)
            target.point_data[str(key)] = np.concatenate((values, generated), axis=0)
        self._map_surface_displacements(source_grid, target)

    def _map_surface_displacements(self, source_grid, target) -> None:
        displacement = displacement_keys(source_grid)
        if displacement is None:
            return
        a = self.generated_source_a
        b = self.generated_source_b
        xi = self.generated_xi
        translations = np.column_stack(
            [source_grid.point_data[key] for key in displacement]
        )
        surface = _interpolate(translations, a, b, xi)
        rotations = rotation_keys(source_grid)
        if rotations is not None:
            theta = np.column_stack(
                [source_grid.point_data[key] for key in rotations]
            )
            theta = _interpolate(theta, a, b, xi)
            surface = surface + np.cross(theta, self.generated_offset)
        start = self.source_point_count
        for index, key in enumerate(displacement):
            values = np.asarray(target.point_data[key], dtype=float).copy()
            values[start:] = surface[:, index]
            target.point_data[key] = values

    def _map_cell_data(self, source_grid, target) -> None:
        for key in source_grid.cell_data.keys():
            values = np.asarray(source_grid.cell_data[key])
            if len(values) == source_grid.n_cells:
                target.cell_data[str(key)] = values[self.cell_source]

    def _attach_mapping(self, source_grid, target) -> None:
        start = self.source_point_count
        source_nodes = (
            source_grid.point_data["node_id"]
            if "node_id" in source_grid.point_data
            else None
        )
        first = np.full(target.n_points, -1, dtype=np.int64)
        second = np.full(target.n_points, -1, dtype=np.int64)
        xi = np.full(target.n_points, np.nan, dtype=float)
        element = np.full(target.n_points, -1, dtype=np.int64)
        if source_nodes is not None:
            ids = np.asarray(source_nodes, dtype=np.int64)
            first[start:] = ids[self.generated_source_a]
            second[start:] = ids[self.generated_source_b]
        xi[start:] = self.generated_xi
        element[start:] = self.generated_solver_element_ids
        target.point_data["_opencae_beam_node_a"] = first
        target.point_data["_opencae_beam_node_b"] = second
        target.point_data["_opencae_beam_xi"] = xi
        target.point_data["_opencae_beam_element"] = element

    def _validate(self, source_grid) -> None:
        if source_grid.n_points != self.source_point_count:
            raise ValueError("Beam representation no longer matches the source mesh")
        if self.source_node_ids is not None and "node_id" in source_grid.point_data:
            current = np.asarray(source_grid.point_data["node_id"])
            if not np.array_equal(self.source_node_ids, current):
                raise ValueError("Beam representation node mapping is stale")
        if self.source_element_ids is not None and "element_id" in source_grid.cell_data:
            current = np.asarray(source_grid.cell_data["element_id"])
            if not np.array_equal(self.source_element_ids, current):
                raise ValueError("Beam representation element mapping is stale")


def build_beam_physical_representation(
    project,
    source_grid,
    progress: ProgressCallback | None = None,
):
    """Build a result representation using exported solver element numbering."""
    return build_beam_physical_representation_from_occurrences(
        beam_occurrences(project),
        source_grid,
        progress=progress,
        source_element_ids=False,
    )


def build_beam_physical_representation_from_occurrences(
    occurrences: Iterable[BeamOccurrence],
    source_grid,
    progress: ProgressCallback | None = None,
    *,
    source_element_ids: bool = True,
):
    """Build physical beam volumes for an explicit set of model occurrences.

    ``source_element_ids`` selects whether the source grid exposes Part-local
    element IDs (editor meshes) or exported solver IDs (stored result meshes).
    """
    occurrences = tuple(occurrences)
    if not occurrences:
        raise ValueError("The current model has no beam elements with assigned profiles")
    if "element_id" not in source_grid.cell_data:
        raise ValueError("The source mesh does not expose element IDs")

    element_ids = np.asarray(source_grid.cell_data["element_id"], dtype=np.int64)
    cell_for_element = (
        {int(element_id): index for index, element_id in enumerate(element_ids)}
        if source_element_ids
        else _solver_cell_map(element_ids)
    )
    generated_sources_a: list[int] = []
    generated_sources_b: list[int] = []
    generated_solver_ids: list[int] = []
    generated_xi: list[float] = []
    generated_offsets: list[np.ndarray] = []
    generated_coefficients: list[tuple[float, float, float]] = []
    generated_cells: list[tuple[int, tuple[int, ...]]] = []
    replaced_cells: set[int] = set()
    total = len(occurrences)

    for position, occurrence in enumerate(occurrences, 1):
        if progress:
            progress(position - 1, total, f"Generating beam {position} of {total}")
        lookup_id = (
            occurrence.source_element_id
            if source_element_ids
            else occurrence.solver_element_id
        )
        cell_index = cell_for_element.get(int(lookup_id))
        if cell_index is None:
            continue
        point_ids = tuple(
            int(value) for value in source_grid.get_cell(cell_index).point_ids
        )
        if len(point_ids) < 2:
            continue
        first, second = point_ids[0], point_ids[1]
        axis = (
            np.asarray(source_grid.points[second], dtype=float)
            - np.asarray(source_grid.points[first], dtype=float)
        )
        frame = _section_frame(axis, occurrence.direction)
        if frame is None:
            continue
        ey, ez = frame
        patches = section_patches(occurrence.profile)
        if not patches:
            continue
        properties = occurrence.profile.properties()
        generated_before = len(generated_sources_a)
        for patch in patches:
            _append_patch(
                patch,
                first,
                second,
                ey,
                ez,
                properties,
                int(occurrence.solver_element_id),
                source_grid.n_points,
                cell_index,
                generated_sources_a,
                generated_sources_b,
                generated_solver_ids,
                generated_xi,
                generated_offsets,
                generated_coefficients,
                generated_cells,
            )
        if len(generated_sources_a) > generated_before:
            replaced_cells.add(cell_index)

    if progress:
        progress(total, total, "Finalizing beam representation")
    if not generated_sources_a:
        raise ValueError("No beam could be mapped to an assigned profile")

    cells: list[int] = []
    celltypes: list[int] = []
    cell_source: list[int] = []
    for cell_index in range(source_grid.n_cells):
        if cell_index in replaced_cells:
            continue
        ids = tuple(int(value) for value in source_grid.get_cell(cell_index).point_ids)
        cells.extend((len(ids), *ids))
        celltypes.append(int(source_grid.celltypes[cell_index]))
        cell_source.append(cell_index)
    for cell_index, ids in generated_cells:
        cells.extend((len(ids), *ids))
        celltypes.append(_VTK_HEXAHEDRON)
        cell_source.append(cell_index)

    source_node_ids = (
        np.asarray(source_grid.point_data["node_id"]).copy()
        if "node_id" in source_grid.point_data
        else None
    )
    return BeamPhysicalRepresentation(
        cells=np.asarray(cells, dtype=np.int64),
        celltypes=np.asarray(celltypes, dtype=np.uint8),
        cell_source=np.asarray(cell_source, dtype=np.int64),
        source_point_count=int(source_grid.n_points),
        source_node_ids=source_node_ids,
        source_element_ids=element_ids.copy(),
        generated_source_a=np.asarray(generated_sources_a, dtype=np.int64),
        generated_source_b=np.asarray(generated_sources_b, dtype=np.int64),
        generated_xi=np.asarray(generated_xi, dtype=float),
        generated_offset=np.asarray(generated_offsets, dtype=float),
        generated_stress_coefficients=np.asarray(generated_coefficients, dtype=float),
        generated_solver_element_ids=np.asarray(generated_solver_ids, dtype=np.int64),
    )


def _solver_cell_map(element_ids: np.ndarray) -> dict[int, int]:
    """Map OpenCAE/FEMaster input IDs to FRD cells for 0- or 1-based FRD IDs."""
    if len(element_ids) == 0:
        return {}
    offset = 1 if int(np.min(element_ids)) == 0 else 0
    return {
        int(result_id) + offset: index
        for index, result_id in enumerate(element_ids)
    }


def _append_patch(
    patch,
    first,
    second,
    ey,
    ez,
    properties,
    solver_element_id,
    source_point_count,
    cell_index,
    sources_a,
    sources_b,
    solver_ids,
    xis,
    offsets,
    coefficients,
    cells,
):
    """Extrude one quadrilateral section patch into one VTK hexahedron."""
    patch = np.asarray(patch, dtype=float)
    if patch.shape != (4, 2) or not np.all(np.isfinite(patch)):
        return

    start = source_point_count + len(sources_a)
    for xi in (0.0, 1.0):
        for y, z in patch:
            sources_a.append(first)
            sources_b.append(second)
            solver_ids.append(solver_element_id)
            xis.append(xi)
            offsets.append(ey * float(y) + ez * float(z))
            coefficients.append(stress_coefficients(properties, float(y), float(z)))

    cells.append(
        (
            cell_index,
            tuple(start + index for index in range(8)),
        )
    )


def _section_frame(axis, preferred):
    length = float(np.linalg.norm(axis))
    if length <= 1.0e-12:
        return None
    ex = axis / length
    ey = np.asarray(preferred, dtype=float)
    ey = ey - np.dot(ey, ex) * ex
    if np.linalg.norm(ey) <= 1.0e-12:
        basis = np.eye(3)[int(np.argmin(np.abs(ex)))]
        ey = basis - np.dot(basis, ex) * ex
    ey = ey / np.linalg.norm(ey)
    ez = np.cross(ex, ey)
    return ey, ez / np.linalg.norm(ez)


def _interpolate(values, source_a, source_b, xi):
    values = np.asarray(values)
    weight_shape = (len(xi),) + (1,) * max(values.ndim - 1, 0)
    weights = xi.reshape(weight_shape)
    return (1.0 - weights) * values[source_a] + weights * values[source_b]


def displacement_keys(grid):
    candidates = (
        ("DISP:D1", "DISP:D2", "DISP:D3"),
        ("DISPLACEMENT:Ux", "DISPLACEMENT:Uy", "DISPLACEMENT:Uz"),
        ("DISP:Ux", "DISP:Uy", "DISP:Uz"),
    )
    return next(
        (group for group in candidates if all(key in grid.point_data for key in group)),
        None,
    )


def rotation_keys(grid):
    candidates = (
        ("DISP:D4", "DISP:D5", "DISP:D6"),
        ("DISPLACEMENT:Rx", "DISPLACEMENT:Ry", "DISPLACEMENT:Rz"),
        ("DISP:R1", "DISP:R2", "DISP:R3"),
        ("ROTATION:Rx", "ROTATION:Ry", "ROTATION:Rz"),
    )
    return next(
        (group for group in candidates if all(key in grid.point_data for key in group)),
        None,
    )


def _is_stress_scalar(name: str | None) -> bool:
    upper = str(name or "").upper()
    block = upper.split(":", 1)[0]
    return block in {"S", "STRESS", "SIGMA"} or "STRESS" in block
