from .conversion import as_region_definition, definition_from_hit, definition_from_local_labels, named_region_definition, reference_point_definition
from .definition import RegionDefinition, RegionSelectionItem, as_selection_item
from .hit import ViewportHit, ViewportSelection
from .labels import selection_item_kind, selection_item_label
from .operands import GeometryOperand, MeshElementOperand, MeshFacetOperand, MeshNodeOperand, NamedRegionOperand, ReferencePointOperand, RegionOperand, UnresolvedOperand, WholeModelOperand, operand_key
from .resolution import ElementOccurrence, FacetOccurrence, NodeOccurrence, ReferencePointOccurrence, RegionDiagnostic, RegionResolver, ResolvedRegion
from .types import NodalLoadDistribution, RegionProjection, RegionRequirement, RegionScope, SelectableKind, SelectionMultiplicity, SelectionOperation, SelectionPolicy
from .validation import region_definition_error, validate_region_definition

__all__ = [name for name in globals() if not name.startswith("_")]

from .facets import element_side_indices
from .local_resolution import local_element_ids, local_geometry_tags
