"""Public API for topology optimization algorithms and FEMaster integration."""

from .deck import DENSITY_FIELD_NAME, render_topology_deck
from .density_state import load_density_state, store_density_volumes
from .density_threshold import active_constraint_limit, automatic_density_threshold
from .filtering import (
    FilterOperators,
    build_density_constraint_matrix,
    build_distance_matrix,
    build_filter_operators,
    minimum_element_distance,
)
from .job_runner import TopologyOptimizationRunner
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
    "TopologyOptimizationRunner",
    "active_constraint_limit",
    "automatic_density_threshold",
    "build_density_constraint_matrix",
    "build_distance_matrix",
    "build_filter_operators",
    "build_mesh_index",
    "dense_values",
    "evaluate_response",
    "minimum_element_distance",
    "load_density_state",
    "optimality_criteria_update",
    "render_topology_deck",
    "store_density_volumes",
    "validate_topology_optimization",
]
