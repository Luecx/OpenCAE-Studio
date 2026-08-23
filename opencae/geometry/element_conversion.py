"""Converts compact mesh blocks between supported element orders/formulations."""

from collections import defaultdict

from opencae.model.element_catalog import CATALOG, resulting_type
from opencae.model.mesh import (
    ElementBlock,
    ElementOrder,
    create_element_definition,
)

from .element_records import records


def convert(part, selected_ids, affected_ids, order, formulation):
    """Convert selected/affected elements and replace compact mesh blocks."""
    mesh = part.mesh
    order = ElementOrder(order)
    elements = records(mesh)
    coordinates = dict(zip(mesh.nodes.ids, mesh.nodes.coordinates))
    midpoints = _existing_midpoints(elements)
    next_id = max(coordinates, default=0) + 1
    groups = defaultdict(list)

    for element in elements.values():
        info = CATALOG[element.topology]
        target_order = (
            order if element.element_id in affected_ids else element.order
        )
        target_form = (
            formulation
            if element.element_id in selected_ids
            and formulation != "Keep Existing"
            else element.formulation
        )
        primary = element.connectivity[: info.primary_nodes]
        connectivity = tuple(primary)
        if target_order == ElementOrder.SECOND:
            extra = []
            for left, right in info.edges:
                edge = tuple(sorted((primary[left], primary[right])))
                if edge not in midpoints:
                    midpoints[edge] = next_id
                    coordinates[next_id] = _middle(
                        coordinates[edge[0]],
                        coordinates[edge[1]],
                    )
                    next_id += 1
                extra.append(midpoints[edge])
            connectivity += tuple(extra)
        groups[
            (element.topology, target_order, target_form)
        ].append((element.element_id, connectivity))

    mesh.replace_element_blocks(
        [_block(key, values) for key, values in groups.items()]
    )
    used = {
        node
        for block in mesh.element_blocks
        for row in block.connectivity
        for node in row
    }
    kept = used | _protected_nodes(part)
    mesh.nodes.ids = sorted(
        node for node in kept if node in coordinates
    )
    mesh.nodes.coordinates = [
        tuple(coordinates[node]) for node in mesh.nodes.ids
    ]
    mesh.entity_nodes = _entity_nodes(
        mesh.entity_nodes,
        midpoints,
        used,
    )
    mesh.node_count = len(mesh.nodes.ids)
    mesh.element_count = sum(
        len(block.ids) for block in mesh.element_blocks
    )
    mesh.status = "Current"
    mesh.revision = f"{mesh.revision or 'mesh'}:converted"


def _existing_midpoints(elements):
    """Index existing second-order edge midpoint nodes."""
    result = {}
    for element in elements.values():
        info = CATALOG[element.topology]
        if element.order != ElementOrder.SECOND:
            continue
        extra = element.connectivity[
            info.primary_nodes : info.primary_nodes + len(info.edges)
        ]
        primary = element.connectivity[: info.primary_nodes]
        for edge, node in zip(info.edges, extra, strict=True):
            result[tuple(sorted((primary[edge[0]], primary[edge[1]])))] = node
    return result


def _block(key, values):
    """Build one compact block for a converted element group."""
    topology, order, formulation = key
    info = CATALOG[topology]
    category, topo = info.category, info.topology
    if topology.value == "line":
        topo = (
            "Beam Elements"
            if formulation == "Beam"
            else "Truss Elements"
        )
    definition = create_element_definition(
        category,
        topo,
        name=resulting_type(topology, order, formulation),
        order=(
            "Quadratic"
            if order == ElementOrder.SECOND
            else "Linear"
        ),
        formulation=formulation,
        gmsh_type=(
            info.gmsh_second
            if order == ElementOrder.SECOND
            else info.gmsh_first
        ),
        count=len(values),
    )
    return ElementBlock(
        definition,
        [value[0] for value in values],
        [value[1] for value in values],
    )


def _middle(first, second):
    """Return the midpoint of two 3D coordinates."""
    return tuple(
        (float(a) + float(b)) * 0.5
        for a, b in zip(first, second, strict=True)
    )


def _protected_nodes(part):
    """Return node IDs that must survive conversion because regions use them."""
    from opencae.model.selection import (
        MeshNodeOperand,
        NamedRegionOperand,
    )

    result = set()
    visited = set()

    def collect(definition):
        for item in definition.items:
            operand = item.operand
            if (
                isinstance(operand, MeshNodeOperand)
                and operand.owner_ref.entity_id == part.id
            ):
                result.add(int(operand.node_id))
            elif (
                isinstance(operand, NamedRegionOperand)
                and operand.region_ref.entity_id not in visited
            ):
                region = next(
                    (
                        value
                        for value in part.regions
                        if value.id == operand.region_ref.entity_id
                    ),
                    None,
                )
                if region is not None:
                    visited.add(region.id)
                    collect(region.definition)

    for region in part.regions:
        if (
            str(getattr(region, "preferred_projection", ""))
            == "nodes"
        ):
            collect(region.definition)
    return result


def _entity_nodes(entity_nodes, midpoints, used):
    """Extend topology node associations with generated midpoint nodes."""
    result = {}
    for name, values in entity_nodes.items():
        nodes = set(map(int, values))
        for edge, midpoint in midpoints.items():
            if (
                midpoint in used
                and edge[0] in nodes
                and edge[1] in nodes
            ):
                nodes.add(midpoint)
        result[name] = sorted(nodes & used)
    return result
