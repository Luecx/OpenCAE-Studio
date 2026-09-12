"""Builds named regions and occurrence-aware targets from domain objects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from opencae.model.entities import Element, Instance, Node, Part, Region
from opencae.model.selection import (
    MeshElementOperand,
    MeshFacetOperand,
    MeshNodeOperand,
    NamedRegionOperand,
    RegionDefinition,
    RegionProjection,
    RegionScope,
)

if TYPE_CHECKING:
    from .model import Model


def create_node_set(
    model: "Model",
    part: Part,
    name: str,
    nodes: Iterable[Node],
) -> Region:
    """Create a named node region containing canonical Node objects."""
    model._require_owned(part, Part)
    node_values = tuple(nodes)
    _require_part_nodes(part, node_values)
    operands = tuple(
        MeshNodeOperand(
            owner=part,
            node=node,
            mesh_revision=part.mesh.revision,
        )
        for node in node_values
    )
    return _append_region(model, part, name, RegionProjection.NODES, operands)


def create_element_set(
    model: "Model",
    part: Part,
    name: str,
    elements: Iterable[Element],
) -> Region:
    """Create a named element region containing canonical Element objects."""
    model._require_owned(part, Part)
    element_values = tuple(elements)
    _require_part_elements(part, element_values)
    operands = tuple(
        MeshElementOperand(
            owner=part,
            element=element,
            mesh_revision=part.mesh.revision,
        )
        for element in element_values
    )
    return _append_region(model, part, name, RegionProjection.ELEMENTS, operands)


def create_surface(
    model: "Model",
    part: Part,
    name: str,
    facets: Iterable[tuple[Element, str]],
) -> Region:
    """Create a named surface from Element objects and local-face labels."""
    model._require_owned(part, Part)
    facet_values = tuple(facets)
    _require_part_elements(part, tuple(element for element, _ in facet_values))
    operands = tuple(
        MeshFacetOperand(
            owner=part,
            element=element,
            local_face=str(local_face),
            mesh_revision=part.mesh.revision,
        )
        for element, local_face in facet_values
    )
    return _append_region(model, part, name, RegionProjection.FACETS, operands)


def create_region_target(
    model: "Model",
    region: Region,
    *,
    instance: Instance | None = None,
) -> RegionDefinition:
    """Wrap a Region object in the occurrence-aware selection value."""
    model._require_owned(region, Region)
    if region.scope == RegionScope.PART:
        part = _owning_part(model, region)
        if instance is None:
            candidates = [
                item
                for item in model.project.assembly.instances
                if not item.suppressed and item.part is part
            ]
            if len(candidates) != 1:
                raise ValueError(
                    f"Part region '{region.name}' requires an Instance; "
                    f"found {len(candidates)} active occurrences"
                )
            instance = candidates[0]
        model._require_owned(instance, Instance)
        if instance.part is not part:
            raise ValueError(
                f"Instance '{instance.name}' does not instantiate Part '{part.name}'"
            )

    return RegionDefinition.from_values(
        (NamedRegionOperand(region=region, instance=instance),)
    )


def _append_region(
    model: "Model",
    part: Part,
    name: str,
    projection: RegionProjection,
    operands: tuple,
) -> Region:
    region = Region(
        name=name,
        scope=RegionScope.PART,
        preferred_projection=projection,
        definition=RegionDefinition.from_values(operands),
        geometry_backed=False,
    )
    part.regions.append(region)
    model._refresh()
    return region


def _owning_part(model: "Model", region: Region) -> Part:
    parent_id = model.project.index.parent_id.get(region.id)
    part = model.project.try_resolve(parent_id, Part)
    if part is None:
        raise ValueError(f"Part region '{region.name}' has no owning Part")
    return part


def _require_part_nodes(part: Part, nodes: tuple[Node, ...]) -> None:
    owned = {node.id: node for node in part.mesh.nodes}
    for node in nodes:
        if not isinstance(node, Node):
            raise TypeError(f"Expected Node, got {type(node).__name__}")
        if owned.get(node.id) is not node:
            raise ValueError(f"Node {node.id} does not belong to Part '{part.name}'")


def _require_part_elements(part: Part, elements: tuple[Element, ...]) -> None:
    owned = {element.id: element for element in part.mesh.iter_elements()}
    for element in elements:
        if not isinstance(element, Element):
            raise TypeError(f"Expected Element, got {type(element).__name__}")
        if owned.get(element.id) is not element:
            raise ValueError(
                f"Element {element.id} does not belong to Part '{part.name}'"
            )
