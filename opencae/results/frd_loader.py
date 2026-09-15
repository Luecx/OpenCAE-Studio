from __future__ import annotations

from pathlib import Path

import numpy as np

from opencae.model.entities.jobs import ResultField
from .beam_physical_representation import (
    build_beam_physical_representation_from_occurrences,
)
from .derived_fields import attach_derived, component_values, derived_names
from .frd_beam_metadata import (
    beam_normal_stress_range,
    beam_occurrences_from_frd,
    read_frd_beam_metadata,
    section_forces_from_frd,
)
from .frd_parser import parse_frd
from .frd_types import FRD_CELL_TYPES


class FrdLoader:
    """Load one FRD into OpenCAE's canonical in-memory result representation."""

    def __init__(self):
        self._cache = {}
        self._beam_representations = {}

    def read(self, path):
        key = str(Path(path).resolve())
        if key not in self._cache:
            self._cache[key] = parse_frd(key)
        return self._cache[key]

    def fields(self, path):
        result = []
        data = self.read(path)
        for block in data.fields:
            result.append(
                ResultField(
                    name=block.name,
                    location="Nodal",
                    components=len(block.components),
                    metadata={
                        "components": list(block.components),
                        "derived": derived_names(block.components),
                        "step_id": block.step_id,
                        "frame_id": block.frame_id,
                        "frame_value": block.frame_value,
                        "block_index": block.block_index,
                    },
                )
            )

        metadata = read_frd_beam_metadata(path)
        frame_values = {
            (int(block.step_id), int(block.frame_id)): float(block.frame_value)
            for block in data.fields
        }
        for step_id, frame_id in sorted(metadata.forces):
            result.append(
                ResultField(
                    name="Beam Normal Stress",
                    location="Element",
                    components=1,
                    metadata={
                        "components": ["Normal Stress"],
                        "derived": [],
                        "default_component": "Normal Stress",
                        "block": "BEAM",
                        "step_id": int(step_id),
                        "frame_id": int(frame_id),
                        "frame_value": frame_values.get(
                            (int(step_id), int(frame_id)), 0.0
                        ),
                        "embedded_beam_normal_stress": True,
                    },
                )
            )
        return result

    def scalar_range(self, path, field):
        if field is None:
            return (0.0, 1.0)
        if field.metadata.get("embedded_beam_normal_stress"):
            values = beam_normal_stress_range(
                path,
                field.metadata.get("step_id"),
                field.metadata.get("frame_id"),
            )
            return values if values is not None else (0.0, 1.0)

        # Beam-enabled FRDs are already expanded at the loader boundary. Derive
        # ranges from that exact canonical grid so the scalar bar includes beam
        # surface values, rotational displacement offsets, and derived stresses.
        if read_frd_beam_metadata(path).beams:
            grid = self.pyvista_grid(
                path,
                field.metadata.get("step_id"),
                field.metadata.get("frame_id"),
            )
            scalar = _field_scalar_name(field)
            store = (
                grid.point_data
                if scalar in grid.point_data
                else grid.cell_data
                if scalar in grid.cell_data
                else None
            )
            if store is not None:
                values = np.asarray(store[scalar], dtype=float)
                finite = values[np.isfinite(values)]
                if len(finite):
                    return float(finite.min()), float(finite.max())

        data = self.read(path)
        block_index = int(field.metadata.get("block_index", 0))
        component = field.metadata.get("component", "Magnitude")
        block = next(
            (item for item in data.fields if item.block_index == block_index),
            None,
        )
        if block is None or not block.values:
            return (0.0, 1.0)
        width = max(len(value) for value in block.values.values())
        values = np.full((len(block.values), width), np.nan)
        for row, value in enumerate(block.values.values()):
            values[row, : len(value)] = value
        scalar = component_values(block.components, values, component)
        finite = scalar[np.isfinite(scalar)]
        return (
            (float(finite.min()), float(finite.max()))
            if len(finite)
            else (0.0, 1.0)
        )

    def pyvista_grid(self, path, step_id=None, frame_id=None):
        """Return the canonical result grid; beam FRDs are expanded here once."""
        import pyvista as pv

        data = self.read(path)
        tags = data.node_order()
        lookup = {tag: index for index, tag in enumerate(tags)}
        cells = []
        types = []
        element_ids = []
        for element_id, code, connectivity in data.elements:
            definition = FRD_CELL_TYPES.get(code)
            if definition is None:
                continue
            vtk_type, count = definition
            nodes = connectivity[:count]
            if len(nodes) != count or any(tag not in lookup for tag in nodes):
                continue
            cells.extend((count, *(lookup[tag] for tag in nodes)))
            types.append(vtk_type)
            element_ids.append(element_id)

        grid = pv.UnstructuredGrid(
            np.asarray(cells, np.int64),
            np.asarray(types, np.uint8),
            data.points(),
        )
        grid.point_data["node_id"] = np.asarray(tags, np.int64)
        grid.cell_data["element_id"] = np.asarray(element_ids, np.int64)
        self._attach_fields(grid, data, tags, step_id, frame_id)
        grid = self._expand_beams(path, grid, step_id, frame_id)
        try:
            grid.set_active_scalars(None)
        except (AttributeError, KeyError, TypeError, ValueError):
            pass
        return grid

    def _expand_beams(self, path, grid, step_id, frame_id):
        source = str(Path(path).resolve())
        occurrences = beam_occurrences_from_frd(source)
        if not occurrences:
            return grid
        representation = self._beam_representations.get(source)
        if representation is None:
            representation = build_beam_physical_representation_from_occurrences(
                occurrences,
                grid,
                source_element_ids=False,
            )
            self._beam_representations[source] = representation
        forces = section_forces_from_frd(source, step_id, frame_id)
        return representation.expand(
            grid,
            element_nodal_forces=forces,
        )

    @staticmethod
    def _attach_fields(grid, data, tags, step_id, frame_id):
        blocks = [
            block
            for block in data.fields
            if (step_id is None or block.step_id == step_id)
            and (frame_id is None or block.frame_id == frame_id)
        ]
        for block in blocks:
            width = max(
                (len(value) for value in block.values.values()),
                default=len(block.components),
            )
            values = np.full((len(tags), width), np.nan)
            for row, tag in enumerate(tags):
                current = block.values.get(tag)
                if current is not None:
                    values[row, : len(current)] = current
            for index, component in enumerate(block.components):
                if index < width:
                    grid.point_data[f"{block.name}:{component}"] = values[:, index]
            physical = values[:, : max(1, min(width, len(block.components)))]
            all_index = next(
                (
                    index
                    for index, name in enumerate(block.components)
                    if name.upper() == "ALL"
                ),
                None,
            )
            grid.point_data[f"{block.name}:Magnitude"] = (
                values[:, all_index]
                if all_index is not None
                else np.linalg.norm(physical, axis=1)
            )
            attach_derived(grid, block.name, block.components, values)


def _field_scalar_name(field) -> str:
    metadata = dict(getattr(field, "metadata", {}) or {})
    block = str(metadata.get("block", getattr(field, "name", "")) or "")
    component = str(metadata.get("component", metadata.get("default_component", "Magnitude")) or "Magnitude")
    return f"{block}:{component}"
