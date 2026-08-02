from PyQt6.QtGui import QStandardItemModel
from .analysis_tree import append_steps
from .part_tree import append_part
from .resource_tree import append_fields, append_materials, append_profiles, append_sections
from .tree_items import append_collection, ensure_expandable, folder


def build_model(project):
    model = QStandardItemModel(); model.setHorizontalHeaderLabels([project.name]); root = model.invisibleRootItem()
    append_materials(root, project.materials); append_sections(root, project.sections, project); append_profiles(root, project.profiles); append_fields(root, project.fields)
    parts = folder("Parts", "parts"); root.appendRow(parts)
    for part in project.parts: append_part(parts, part)
    ensure_expandable(parts, project.parts, "No parts")
    _append_assembly(root, project)
    append_collection(root, "Constraints", project.assembly.constraints, "constraints")
    boundary = folder("Boundary Conditions", "boundary_conditions"); root.appendRow(boundary)
    append_collection(boundary, "Supports", project.supports, "supports")
    append_collection(boundary, "Loads", project.loads, "loads")
    append_steps(root, project.analyses)
    return model


def _append_assembly(root, project):
    assembly = folder("Assembly", "assembly"); root.appendRow(assembly)
    collections = (
        ("Instances", project.assembly.instances, "instances"), ("Node Sets", project.assembly.node_sets, "asm_node_sets"),
        ("Element Sets", project.assembly.element_sets, "asm_element_sets"), ("Surfaces", project.assembly.surfaces, "asm_surfaces"),
        ("Coordinate Systems", project.assembly.coordinate_systems, "asm_coordinate_systems"),
        ("Reference Points", project.assembly.reference_points, "asm_reference_points"),
    )
    for title, collection, kind in collections: append_collection(assembly, title, collection, kind)
