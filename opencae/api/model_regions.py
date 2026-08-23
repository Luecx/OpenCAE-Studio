"""Builds named regions and occurrence-aware targets for the Model facade."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from opencae.model.core import EntityRef
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
    """Create a named node region from Node objects owned by ``part``."""
    model._require_owned(part, Part)
    node_values = tuple(nodes)
    _require_part_nodes(part, node_values)
    operands = tuple(
        MeshNodeOperand(
            owner_ref=EntityRef.of(part, "Part"),
            node_id=node.id,
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
    """Create a named element region from Element objects owned by ``part``."""
    model._require_owned(part, Part)
    element_values = tuple(elements)
    _require_part_elements(part, element_values)
    operands = tuple(
        MeshElementOperand(
            owner_ref=EntityRef.of(part, "Part"),
            element_id=element.id,
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
    """Create a named surface from element/local-face pairs."""
    model._require_owned(part, Part)
    facet_values = tuple(facets)
    _require_part_elements(part, tuple(element for element, _ in facet_values))
    operands = tuple(
        MeshFacetOperand(
            owner_ref=EntityRef.of(part, "Part"),
            element_id=element.id,
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
    """Convert a Region object into an occurrence-aware target definition."""
    model._require_owned(region, Region)
    instance_ref = None
    if region.scope == RegionScope.PART:
        part = _owning_part(model, region)

        # Auto-selection is safe only for exactly one active occurrence.
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
                f"Instance '{instance.name}' does not instantiate "
                f"Part '{part.name}'"
            )
        instance_ref = EntityRef.of(instance, "Instance")

    return RegionDefinition.from_values(
        (
            NamedRegionOperand(
                region_ref=EntityRef.of(region, "Region"),
                instance_ref=instance_ref,
            ),
        )
    )


def _append_region(
    model: "Model",
    part: Part,
    name: str,
    projection: RegionProjection,
    operands: tuple,
) -> Region:
    """Attach one compact Region representation to a Part."""
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
    """Return the Part that structurally owns a part-scoped Region."""
    parent_id = model.project.index.parent_id.get(region.id)
    part = model.project.try_resolve(parent_id, Part)
    if part is None:
        raise ValueError(f"Part region '{region.name}' has no owning Part")
    return part


def _require_part_nodes(part: Part, nodes: tuple[Node, ...]) -> None:
    """Reject Node values that are not present in the Part mesh."""
    owned = {node.id: node for node in part.mesh.node_objects()}
    for node in nodes:
        if not isinstance(node, Node):
            raise TypeError(f"Expected Node, got {type(node).__name__}")
        if owned.get(node.id) != node:
            raise ValueError(f"Node {node.id} does not belong to Part '{part.name}'")


def _require_part_elements(part: Part, elements: tuple[Element, ...]) -> None:
    """Reject Element values that are not present in the Part mesh."""
    owned = {element.id: element for element in part.mesh.element_objects()}
    for element in elements:
        if not isinstance(element, Element):
            raise TypeError(f"Expected Element, got {type(element).__name__}")
        if owned.get(element.id) != element:
            raise ValueError(
                f"Element {element.id} does not belong to Part '{part.name}'"
            )
