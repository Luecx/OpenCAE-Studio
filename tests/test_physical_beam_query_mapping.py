"""Physical-beam query mapping must expose logical FE nodes, not display points."""

from __future__ import annotations

import numpy as np
import pyvista as pv

from opencae.model.entities.profiles import RectangleProfile
from opencae.results.beam_physical_model import BeamOccurrence
from opencae.results.beam_physical_representation import (
    PHYSICAL_BEAM_CELL,
    build_beam_physical_representation_from_occurrences,
)
from opencae.ui.other.viewport.result_query import _logical_node_index, _node_ids


def test_generated_hexa_points_map_back_to_beam_end_nodes():
    source = pv.UnstructuredGrid(
        np.asarray((2, 0, 1), dtype=np.int64),
        np.asarray((3,), dtype=np.uint8),
        np.asarray(((0.0, 0.0, 0.0), (2.0, 0.0, 0.0))),
    )
    source.point_data["node_id"] = np.asarray((11, 22), dtype=np.int64)
    source.cell_data["element_id"] = np.asarray((7,), dtype=np.int64)
    profile = RectangleProfile(
        name="R",
        dimensions={"width": 2.0, "height": 1.0},
    )
    occurrence = BeamOccurrence(
        solver_element_id=7,
        part_id="part",
        instance_id="",
        source_element_id=7,
        connectivity=(11, 22),
        n1=(0.0, 1.0, 0.0),
        section=None,
        profile=profile,
    )

    representation = build_beam_physical_representation_from_occurrences(
        (occurrence,),
        source,
        source_element_ids=True,
    )
    expanded = representation.expand(source)
    physical_cells = np.flatnonzero(
        np.asarray(expanded.cell_data[PHYSICAL_BEAM_CELL], dtype=bool)
    )
    assert len(physical_cells) == 4
    cell = expanded.get_cell(int(physical_cells[0]))

    assert _logical_node_index(expanded, 2) == 0
    assert _logical_node_index(expanded, 6) == 1
    assert _node_ids(expanded, cell.point_ids) == [11, 11, 11, 11, 22, 22, 22, 22]
