from .tree_items import append_collection, folder, item
from opencae.model.selection import RegionProjection, selection_item_label
from opencae.model.entities.regions.collection import regions_with_projection


def append_part(parts, part):
    part_node = item(part.name, part, "part", is_folder=True, part_id=part.id)
    parts.appendRow(part_node)
    _append_geometry(part_node, part)
    _append_datums(part_node, part)
    _append_mesh(part_node, part)
    regions = folder("Regions", "regions", part.id, count=len(part.regions))
    part_node.appendRow(regions)
    append_collection(regions, "Node Regions", regions_with_projection(part.regions, RegionProjection.NODES), "node_sets", part.id)
    append_collection(regions, "Element Regions", regions_with_projection(part.regions, RegionProjection.ELEMENTS), "element_sets", part.id)
    append_collection(regions, "Surface Regions", regions_with_projection(part.regions, RegionProjection.FACETS), "surfaces", part.id)
    collections = (
        ("Coordinate Systems", part.coordinate_systems, "coordinate_systems"),
        ("Reference Points", part.reference_points, "reference_points"),
        ("Orientations", part.orientations, "orientations"),
        ("Section Assignments", part.section_assignments, "section_assignments"),
    )
    for title, collection, kind in collections:
        append_collection(part_node, title, collection, kind, part.id)



def _append_datums(part_node, part):
    datums = folder("Datums", "datums", part.id, count=len(getattr(part, "datums", ()))); part_node.appendRow(datums)
    if not getattr(part, "datums", None):
        placeholder = item("No datums", None, "empty", part_id=part.id); placeholder.setEnabled(False); datums.appendRow(placeholder)
    for datum in getattr(part, "datums", ()):
        datums.appendRow(item(datum.name, datum, f"datum_{datum.datum_type.lower()}", part_id=part.id))


def _append_geometry(part_node, part):
    geometry = folder("Geometry", "geometry", part.id, count=len(part.geometry))
    part_node.appendRow(geometry)
    if not part.geometry:
        geometry.appendRow(item("No geometry", None, "empty", part_id=part.id))
    for feature in part.geometry:
        prefix = "⊘ " if feature.suppressed else ""
        suffix = "  [failed]" if feature.status == "Failed" else ""
        geometry.appendRow(item(prefix + feature.name + suffix, feature, "geometry_feature", part_id=part.id))


def _append_mesh(part_node, part):
    mesh_member_count = part.mesh.node_count + sum(
        definition.count for definition in part.mesh.elements
    )
    mesh = folder("Mesh", "mesh", part.id, count=mesh_member_count)
    part_node.appendRow(mesh)
    for seed in part.mesh.seeds:
        mesh.appendRow(item(seed.name, seed, "seed", part_id=part.id))
    for control in part.mesh.element_controls:
        target = "Entire Part" if control.target.empty else ", ".join(selection_item_label(None, value) for value in control.target.items)
        mesh.appendRow(item(control.name, control, "element_control", f"[{control.order.value} | {target}]", part_id=part.id))
    mesh.appendRow(item("Nodes", {"count": part.mesh.node_count, "status": part.mesh.status}, "nodes", f"({part.mesh.node_count:,})", part_id=part.id))
    elements = folder("Elements", "elements", part.id, count=sum(definition.count for definition in part.mesh.elements))
    mesh.appendRow(elements)
    for category in ("Line Elements", "Shell Elements", "2D Elements", "Solid Elements"):
        definitions = [entry for entry in part.mesh.elements if entry.category == category]
        if definitions:
            _append_element_category(elements, category, definitions, part.id)


def _append_element_category(elements, category, definitions, part_id):
    category_node = folder(category, "element_category", part_id, count=sum(definition.count for definition in definitions))
    elements.appendRow(category_node)
    for definition in definitions:
        category_node.appendRow(item(definition.name, definition, "element_definition", f"({definition.count:,})", part_id=part_id))
