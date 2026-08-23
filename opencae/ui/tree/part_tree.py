"""Builds the Part subtree shown in the project tree."""

from opencae.model.entities.regions.collection import regions_with_projection
from opencae.model.selection import RegionProjection, selection_item_label

from .tree_items import append_collection, folder, item


def append_part(parts, part):
    """Append one Part and its geometry, mesh, regions, and resources."""
    part_node = item(
        part.name, part, "part", is_folder=True, part_id=part.id
    )
    parts.appendRow(part_node)
    _append_geometry(part_node, part)
    _append_datums(part_node, part)
    _append_mesh(part_node, part)

    regions = folder("Regions", "regions", part.id, count=len(part.regions))
    part_node.appendRow(regions)
    for title, projection, kind in (
        ("Node Regions", RegionProjection.NODES, "node_sets"),
        ("Element Regions", RegionProjection.ELEMENTS, "element_sets"),
        ("Surface Regions", RegionProjection.FACETS, "surfaces"),
    ):
        append_collection(
            regions,
            title,
            regions_with_projection(part.regions, projection),
            kind,
            part.id,
        )

    for title, collection, kind in (
        ("Coordinate Systems", part.coordinate_systems, "coordinate_systems"),
        ("Reference Points", part.reference_points, "reference_points"),
        ("Orientations", part.orientations, "orientations"),
        ("Section Assignments", part.section_assignments, "section_assignments"),
    ):
        append_collection(part_node, title, collection, kind, part.id)


def _append_datums(part_node, part):
    """Append the Part's datum folder and datum entities."""
    datums = folder(
        "Datums", "datums", part.id, count=len(getattr(part, "datums", ()))
    )
    part_node.appendRow(datums)
    if not getattr(part, "datums", None):
        placeholder = item("No datums", None, "empty", part_id=part.id)
        placeholder.setEnabled(False)
        datums.appendRow(placeholder)
    for datum in getattr(part, "datums", ()):
        datums.appendRow(
            item(
                datum.name,
                datum,
                f"datum_{datum.datum_type.lower()}",
                part_id=part.id,
            )
        )


def _append_geometry(part_node, part):
    """Append ordered geometry-history features."""
    geometry = folder("Geometry", "geometry", part.id, count=len(part.geometry))
    part_node.appendRow(geometry)
    if not part.geometry:
        geometry.appendRow(item("No geometry", None, "empty", part_id=part.id))
    for feature in part.geometry:
        prefix = "⊘ " if feature.suppressed else ""
        suffix = "  [failed]" if feature.status == "Failed" else ""
        geometry.appendRow(
            item(
                prefix + feature.name + suffix,
                feature,
                "geometry_feature",
                part_id=part.id,
            )
        )


def _append_mesh(part_node, part):
    """Append mesh controls, node summary, and canonical definitions."""
    definitions = part.mesh.element_definitions
    mesh_member_count = part.mesh.node_count + sum(
        definition.count for definition in definitions
    )
    mesh = folder("Mesh", "mesh", part.id, count=mesh_member_count)
    part_node.appendRow(mesh)

    for seed in part.mesh.seeds:
        mesh.appendRow(item(seed.name, seed, "seed", part_id=part.id))
    for control in part.mesh.element_controls:
        target = (
            "Entire Part"
            if control.target.empty
            else ", ".join(
                selection_item_label(None, value)
                for value in control.target.items
            )
        )
        mesh.appendRow(
            item(
                control.name,
                control,
                "element_control",
                f"[{control.order.value} | {target}]",
                part_id=part.id,
            )
        )

    mesh.appendRow(
        item(
            "Nodes",
            {"count": part.mesh.node_count, "status": part.mesh.status},
            "nodes",
            f"({part.mesh.node_count:,})",
            part_id=part.id,
        )
    )
    elements = folder(
        "Elements",
        "elements",
        part.id,
        count=sum(definition.count for definition in definitions),
    )
    mesh.appendRow(elements)
    for category in (
        "Line Elements",
        "Shell Elements",
        "2D Elements",
        "Solid Elements",
    ):
        category_definitions = [
            entry for entry in definitions if entry.category == category
        ]
        if category_definitions:
            _append_element_category(
                elements, category, category_definitions, part.id
            )


def _append_element_category(elements, category, definitions, part_id):
    """Append one element-category folder and its definitions."""
    category_node = folder(
        category,
        "element_category",
        part_id,
        count=sum(definition.count for definition in definitions),
    )
    elements.appendRow(category_node)
    for definition in definitions:
        category_node.appendRow(
            item(
                definition.name,
                definition,
                "element_definition",
                f"({definition.count:,})",
                part_id=part_id,
            )
        )
