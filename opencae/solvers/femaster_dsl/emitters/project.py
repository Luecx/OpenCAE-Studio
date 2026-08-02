from __future__ import annotations

from ..command import command
from .assembly_regions import write_assembly_regions
from .constraints import write_constraint
from .loads import write_load, write_support
from .mesh import _safe, write_part_mesh
from .resources import write_field, write_material, write_orientation, write_profile, write_section
from .reference_points import write_assembly_reference_points


def write_project(project, writer, context):
    command(writer, "MODEL", NAME=context.solver_name(project, project.name))
    instances = [item for item in project.assembly.instances if not item.suppressed]
    if not instances: raise ValueError("FEMaster export requires at least one active assembly instance")
    node_offset = element_offset = 0; exported = []; aliases = {}
    context.options["region_aliases"] = aliases; context.options["entity_aliases"] = {}; context.options["part_region_aliases"] = {}; context.options["part_region_data"] = {}
    for index, instance in enumerate(instances):
        part = _part_for(project, instance, index)
        if part is None: continue
        node_map, element_map, node_offset, element_offset = write_part_mesh(part, writer, context, instance, node_offset, element_offset)
        exported.append((part, instance, node_map, element_map))
    node_offset = write_assembly_reference_points(project, writer, context, node_offset)
    write_assembly_regions(project, exported, writer, context)
    for system in (*project.assembly.coordinate_systems, *(item for part in project.parts for item in part.coordinate_systems)): write_orientation(system, writer, context)
    for material in project.materials: write_material(material, writer, context)
    for profile in project.profiles: write_profile(profile, writer, context)
    for field in project.fields: write_field(field, writer, context)
    for part, instance, _node_map, _element_map in exported:
        prefix = _safe(instance.name if instance else part.name)
        for assignment in part.section_assignments:
            section = project.try_resolve(assignment.section_ref)
            region = project.try_resolve(assignment.region_ref)
            if section is None or region is None: continue
            elset = context.options.get("instance_region_aliases", {}).get((instance.id, region.id), f"{prefix}_{_safe(region.name)}")
            orientation = project.try_resolve(assignment.orientation_ref) if assignment.orientation_ref else None
            orientation_name = context.solver_name(orientation, orientation.name) if orientation else None
            write_section(section, elset, orientation_name, writer, context)
    for constraint in project.assembly.constraints: write_constraint(constraint, writer, context)
    for support in project.supports: write_support(support, writer, context)
    for load in project.loads: write_load(load, writer, context)
    if context.analysis: context.analysis.write_femaster(writer, context)
    else:
        for analysis in project.analyses: analysis.write_femaster(writer, context)
    command(writer, "END")


def _part_for(project, instance, index):
    if instance is None: return project.parts[index] if index < len(project.parts) else None
    return project.try_resolve(instance.part_ref)
