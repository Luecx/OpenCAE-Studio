from __future__ import annotations

from .definition import RegionDefinition
from .operands import (
    GeometryOperand, MeshElementOperand, NamedRegionOperand, WholeModelOperand,
)


def local_geometry_tags(part, definition, dimension: int) -> set[int]:
    """Resolve geometry operands without requiring a complete Project.

    This path is used during meshing, before mesh-based RegionResolver
    projections are available. Named regions are expanded within the owning
    Part and cycles are rejected.
    """
    result: set[int] = set()
    _collect_geometry(part, RegionDefinition.from_values(definition), int(dimension), result, set())
    return result


def local_element_ids(part, definition) -> set[int]:
    """Resolve a part-local region to persistent element IDs."""
    available = {
        int(element_id)
        for block in part.mesh.element_blocks
        for element_id in block.ids
    }
    definition = RegionDefinition.from_values(definition)
    if definition.empty:
        return available
    result: set[int] = set()
    _collect_elements(part, definition, result, set())
    return result & available


def _collect_geometry(part, definition, dimension, result, stack):
    for item in definition.items:
        operand = item.operand
        if isinstance(operand, GeometryOperand) and operand.dimension == dimension:
            result.add(int(operand.tag))
        elif isinstance(operand, NamedRegionOperand):
            region = next((value for value in part.regions if value.id == operand.region_ref.entity_id), None)
            if region is None or region.id in stack:
                continue
            _collect_geometry(part, region.definition, dimension, result, {*stack, region.id})


def _collect_elements(part, definition, result, stack):
    from opencae.geometry.element_targets import elements_from_geometry_label

    for item in definition.items:
        operand = item.operand
        if isinstance(operand, MeshElementOperand):
            result.add(int(operand.element_id))
        elif isinstance(operand, GeometryOperand):
            label = f"{('Vertex', 'Edge', 'Face', 'Cell')[operand.dimension]}-{operand.tag}"
            result.update(elements_from_geometry_label(part, label))
        elif isinstance(operand, NamedRegionOperand):
            region = next((value for value in part.regions if value.id == operand.region_ref.entity_id), None)
            if region is None or region.id in stack:
                continue
            _collect_elements(part, region.definition, result, {*stack, region.id})
        elif isinstance(operand, WholeModelOperand):
            for block in part.mesh.element_blocks:
                result.update(int(value) for value in block.ids)
