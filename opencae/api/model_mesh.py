"""Creates authored nodes and elements for the public Model facade."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from opencae.model.entities import Element, Node, Part

if TYPE_CHECKING:
    from .model import Model


def create_node(
    model: "Model",
    part: Part,
    coordinates: tuple[float, float, float],
    *,
    node_id: int | None = None,
) -> Node:
    """Create one Node inside a validated Part."""
    model._require_owned(part, Part)
    return part.mesh.add_node(coordinates, node_id)


def create_element(
    model: "Model",
    part: Part,
    element_type: type[Element],
    nodes: Iterable[Node],
    *,
    element_id: int | None = None,
) -> Element:
    """Create one Element and verify all connectivity nodes belong to the Part."""
    model._require_owned(part, Part)
    node_values = tuple(nodes)

    # A Node is a lightweight authored value rather than an Entity. Ownership is
    # therefore proven against the Part's node table instead of ProjectIndex.
    owned = {node.id: node for node in part.mesh.nodes}
    for node in node_values:
        if not isinstance(node, Node):
            raise TypeError(
                "Element connectivity must contain Node objects, "
                f"got {type(node).__name__}"
            )
        if owned.get(node.id) != node:
            raise ValueError(
                f"Node {node.id} does not belong to Part '{part.name}'"
            )

    return part.mesh.add_element(element_type, node_values, element_id)
