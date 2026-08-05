"""Public API for topology optimization algorithms and FEMaster integration."""

from .deck import DENSITY_FIELD_NAME, render_topology_deck
from .filtering import (
    FilterOperators,
    build_density_constraint_matrix,
    build_distance_matrix,
    build_filter_operators,
    minimum_element_distance,
)
from .mesh_index import TopologyMeshIndex, build_mesh_index
from .oc import OcUpdate, optimality_criteria_update
from .res_field import ResField
from .res_field_reader import ResFieldReader
from .res_format_error import ResFormatError
from .res_values import dense_values
from .responses import ResponseEvaluation, evaluate_response
from .validation import validate_topology_optimization

__all__ = [
    "DENSITY_FIELD_NAME",
    "FilterOperators",
    "OcUpdate",
    "ResField",
    "ResFieldReader",
    "ResFormatError",
    "ResponseEvaluation",
    "TopologyMeshIndex",
    "build_density_constraint_matrix",
    "build_distance_matrix",
    "build_filter_operators",
    "build_mesh_index",
    "dense_values",
    "evaluate_response",
    "minimum_element_distance",
    "optimality_criteria_update",
    "render_topology_deck",
    "validate_topology_optimization",
]
