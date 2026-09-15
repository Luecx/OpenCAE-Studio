"""Load standalone FEMaster RES results with a same-stem OpenCAE model snapshot."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from opencae.model.entities.jobs import ResultField
from opencae.model.entities.profiles.section_geometry import section_patches
from .beam_physical_model import beam_occurrences
from .beam_physical_stress import stress_coefficients
from .derived_fields import attach_derived, component_values, derived_names
from .femaster_res_section_forces import load_local_section_forces
from .res_model_snapshot import ResultModel, load_result_model, resolve_model_path
from .res_parser import ResData, ResFieldBlock, parse_res, value_matrix

_IGNORED_GENERAL_DOMAINS = {"ELEMENT_NODAL", "ELEMENT_IP", "ELEMENT_MP"}
_SECTION_FORCE_NAME = "LOCAL_SECTION_FORCES"
_BEAM_FIELD_NAME = "Beam Normal Stress"
_BEAM_BLOCK = "BEAM_STRESS"


class ResLoader:
    """Read native FEMaster RES as an independent result source."""

    def __init__(self) -> None:
        self._result_cache: dict[str, ResData] = {}
        self._model_cache: dict[tuple[str, str], ResultModel] = {}

    def read(self, path) -> ResData:
        source = _require_res(path)
        key = str(source.resolve())
        if key not in self._result_cache:
            self._result_cache[key] = parse_res(source)
        return self._result_cache[key]

    def model_path(self, path) -> Path:
        return resolve_model_path(_require_res(path))

    def _model(self, path) -> ResultModel:
        source = _require_res(path)
        model_path = self.model_path(source)
        key = (str(source.resolve()), str(model_path.resolve()))
        if key not in self._model_cache:
            self._model_cache[key] = load_result_model(source)
        return self._model_cache[key]

    def project(self, path):
        return self._model(path).project

    def element_id_map(self, path) -> dict[str, int]:
        model = self._model(path)
        return {
            key: int(value)
            for key, value in zip(model.element_keys, model.element_ids, strict=True)
        }

    def fields(self, path):
        model = self._model(path)
        data = self.read(path)
        result = []
        for block in data.fields:
            if block.domain in _IGNORED_GENERAL_DOMAINS:
                continue
            if block.domain not in {"NODE", "ELEMENT"}:
                continue
            result.append(
                ResultField(
                    name=block.display_name,
                    location="Nodal" if block.domain == "NODE" else "Element",
                    components=len(block.components),
                    metadata={
                        "block": block.block_name,
                        "components": list(block.components),
                        "derived": (
                            derived_names(block.components)
                            if block.domain == "NODE"
                            else []
                        ),
                        "step_id": block.loadcase,
                        "frame_id": block.frame_id,
                        "frame_value": block.frame_value,
                        "block_index": block.block_index,
                        "association": "point" if block.domain == "NODE" else "cell",
                        "source_format": "res",
                    },
                )
            )

        if beam_occurrences(model.project):
            seen = set()
            for block in data.fields:
                if (
                    block.name.upper() != _SECTION_FORCE_NAME
                    or block.domain != "ELEMENT_NODAL"
                ):
                    continue
                key = (block.loadcase, block.frame_id)
                if key in seen:
                    continue
                seen.add(key)
                result.append(
                    ResultField(
                        name=_BEAM_FIELD_NAME,
                        location="Nodal",
                        components=1,
                        metadata={
                            "block": _BEAM_BLOCK,
                            "components": ["Normal Stress"],
                            "derived": [],
                            "step_id": block.loadcase,
                            "frame_id": block.frame_id,
                            "frame_value": block.frame_value,
                            "association": "point",
                            "source_format": "res",
                            "beam_section_stress": True,
                        },
                    )
                )
        return result

    def scalar_range(self, path, field):
        if field is None:
            return (0.0, 1.0)
        if field.metadata.get("beam_section_stress"):
            return self._beam_stress_range(path, field)
        block = self._block(path, field)
        if block is None or not block.values:
            return (0.0, 1.0)
        scalar = component_values(
            block.components,
            value_matrix(block),
            field.metadata.get("component", "Magnitude"),
        )
        finite = scalar[np.isfinite(scalar)]
        return (
            (float(finite.min()), float(finite.max()))
            if len(finite)
            else (0.0, 1.0)
        )

    def pyvista_grid(self, path, step_id=None, frame_id=None):
        import pyvista as pv

        source = _require_res(path)
        model = self._model(source)
        data = self.read(source)
        grid = pv.UnstructuredGrid(
            model.cells.copy(), model.celltypes.copy(), model.points.copy()
        )
        grid.point_data["node_id"] = model.node_ids.copy()
        grid.cell_data["element_id"] = model.element_ids.copy()
        self._attach_fields(grid, data, model, step_id, frame_id)
        if self._has_section_forces(data, step_id, frame_id):
            empty = np.full(grid.n_points, np.nan, dtype=float)
            grid.point_data[f"{_BEAM_BLOCK}:Magnitude"] = empty.copy()
            grid.point_data[f"{_BEAM_BLOCK}:Normal Stress"] = empty.copy()
        try:
            grid.set_active_scalars(None)
        except (AttributeError, KeyError, TypeError, ValueError):
            pass
        return grid

    def _block(self, path, field) -> ResFieldBlock | None:
        block_index = field.metadata.get("block_index")
        if block_index is None:
            return None
        return next(
            (
                block
                for block in self.read(path).fields
                if block.block_index == int(block_index)
            ),
            None,
        )

    @staticmethod
    def _has_section_forces(data, step_id, frame_id) -> bool:
        return any(
            block.name.upper() == _SECTION_FORCE_NAME
            and block.domain == "ELEMENT_NODAL"
            and (step_id is None or block.loadcase == int(step_id))
            and (frame_id is None or block.frame_id == int(frame_id))
            for block in data.fields
        )

    @staticmethod
    def _attach_fields(grid, data, model, step_id, frame_id) -> None:
        for block in data.fields:
            if block.domain not in {"NODE", "ELEMENT"}:
                continue
            if step_id is not None and block.loadcase != int(step_id):
                continue
            if frame_id is not None and block.frame_id != int(frame_id):
                continue
            target = grid.point_data if block.domain == "NODE" else grid.cell_data
            keys = model.node_keys if block.domain == "NODE" else model.element_keys
            ids = model.node_ids if block.domain == "NODE" else model.element_ids
            count = len(ids)
            values = np.full((count, len(block.components)), np.nan, dtype=float)

            if len(block.values) == count:
                for row, current in enumerate(block.values.values()):
                    width = min(values.shape[1], len(current))
                    values[row, :width] = current[:width]
            else:
                lookup = {key: index for index, key in enumerate(keys)}
                lookup.update({str(int(value)): index for index, value in enumerate(ids)})
                for indices, current in block.values.items():
                    if not indices:
                        continue
                    row = lookup.get(str(indices[0]))
                    if row is None:
                        continue
                    width = min(values.shape[1], len(current))
                    values[row, :width] = current[:width]

            for index, component in enumerate(block.components):
                target[f"{block.block_name}:{component}"] = values[:, index]
            target[f"{block.block_name}:Magnitude"] = np.linalg.norm(values, axis=1)
            if block.domain == "NODE":
                attach_derived(grid, block.block_name, block.components, values)

    def _beam_stress_range(self, path, field):
        model = self._model(path)
        forces = load_local_section_forces(
            path, int(field.metadata.get("step_id", 1))
        )
        values = []
        for occurrence in beam_occurrences(model.project):
            rows = forces.get(int(occurrence.solver_element_id))
            if rows is None or not len(rows):
                continue
            properties = occurrence.profile.properties()
            for patch in section_patches(occurrence.profile):
                for y, z in np.asarray(patch, dtype=float):
                    coefficients = np.asarray(
                        stress_coefficients(properties, float(y), float(z)),
                        dtype=float,
                    )
                    for row in rows[:2]:
                        row = np.asarray(row, dtype=float)
                        if len(row) >= 6:
                            values.append(
                                coefficients[0] * row[0]
                                + coefficients[1] * row[4]
                                + coefficients[2] * row[5]
                            )
        finite = np.asarray(values, dtype=float)
        finite = finite[np.isfinite(finite)]
        if not len(finite):
            return (0.0, 1.0)
        if str(field.metadata.get("component", "Magnitude")).casefold() == "magnitude":
            finite = np.abs(finite)
        return float(finite.min()), float(finite.max())


def _require_res(path) -> Path:
    source = Path(path)
    if source.suffix.lower() != ".res":
        raise ValueError("FEMaster RES loader requires a .res result file")
    if not source.is_file():
        raise FileNotFoundError(f"Result file does not exist: {source}")
    return source
