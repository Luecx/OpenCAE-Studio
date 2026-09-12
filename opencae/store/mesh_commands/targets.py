"""Shared addressing and restoration helpers for reversible mesh edits."""

from copy import deepcopy

from opencae.model.entities.parts import Part
from opencae.model.selection import MeshElementOperand, MeshFacetOperand, MeshNodeOperand


def part_for(project, part_id: str) -> Part:
    """Resolve the Part addressed by one mesh command."""
    part = project.try_resolve(part_id)
    if not isinstance(part, Part):
        raise ValueError(f"Part '{part_id}' does not exist")
    return part


def metadata(mesh) -> tuple:
    """Capture small derived/lifecycle state invalidated by a manual edit."""
    return (
        deepcopy(mesh.lifecycle),
        deepcopy(mesh.quality),
        mesh.mesh_dimension,
    )


def restore_metadata(mesh, values: tuple) -> None:
    """Restore lifecycle/quality state after undoing a mesh edit."""
    lifecycle, quality, mesh_dimension = values
    mesh.lifecycle = deepcopy(lifecycle)
    mesh.quality = deepcopy(quality)
    mesh.mesh_dimension = mesh_dimension


def associations(mesh, *, node_ids=(), element_ids=()) -> dict:
    """Capture only CAD-association entries touched by an edit."""
    nodes = {int(value) for value in node_ids}
    elements = {int(value) for value in element_ids}
    return {
        "entity_nodes": {
            key: [value for value in values if int(value) in nodes]
            for key, values in mesh.entity_nodes.items()
            if any(int(value) in nodes for value in values)
        },
        "entity_elements": {
            key: [value for value in values if int(value) in elements]
            for key, values in mesh.entity_elements.items()
            if any(int(value) in elements for value in values)
        },
        "entity_facets": {
            key: [value for value in values if int(value[0]) in elements]
            for key, values in mesh.entity_facets.items()
            if any(int(value[0]) in elements for value in values)
        },
    }


def restore_associations(mesh, values: dict) -> None:
    """Merge command-local CAD memberships back into the live mesh."""
    for attribute, additions in values.items():
        target = getattr(mesh, attribute)
        for key, items in additions.items():
            current = list(target.get(key, ()))
            for item in items:
                if item not in current:
                    current.append(item)
            target[key] = current


def remove_region_references(part, *, node_ids=(), element_ids=()) -> dict:
    """Remove direct mesh operands invalidated by deletion and return snapshots."""
    nodes = {int(value) for value in node_ids}
    elements = {int(value) for value in element_ids}
    previous = {}
    for region in part.regions:
        retained = []
        changed = False
        for item in region.definition.items:
            operand = item.operand
            remove = (
                isinstance(operand, MeshNodeOperand)
                and operand.node_id in nodes
            ) or (
                isinstance(operand, (MeshElementOperand, MeshFacetOperand))
                and operand.element_id in elements
            )
            if remove:
                changed = True
            else:
                retained.append(item)
        if changed:
            previous[region.id] = deepcopy(region.definition)
            region.definition = type(region.definition)(tuple(retained))
    return previous


def restore_region_references(part, values: dict) -> None:
    """Restore region definitions removed by a reversible deletion."""
    by_id = {region.id: region for region in part.regions}
    for region_id, definition in values.items():
        if region_id in by_id:
            by_id[region_id].definition = deepcopy(definition)
