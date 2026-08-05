"""Renders one FEMaster LINEARSTATICTOPO deck for a density evaluation."""

from __future__ import annotations

import numpy as np

from opencae.model.core import DeckWriter, ExportContext
from opencae.model.selection import RegionProjection
from opencae.solvers.femaster_dsl.command import command
from opencae.solvers.femaster_dsl.emitters.assembly_regions import write_assembly_regions
from opencae.solvers.femaster_dsl.emitters.constraints import write_constraint
from opencae.solvers.femaster_dsl.emitters.loads import write_load, write_support
from opencae.solvers.femaster_dsl.emitters.mesh import _safe, write_part_mesh
from opencae.solvers.femaster_dsl.emitters.reference_points import (
    write_assembly_reference_points,
)
from opencae.solvers.femaster_dsl.emitters.region_materialization import (
    materialize_region,
)
from opencae.solvers.femaster_dsl.emitters.resources import (
    write_field,
    write_material,
    write_orientation,
    write_profile,
    write_section,
)

DENSITY_FIELD_NAME = "OPENCAE_TOPO_DENSITY"


def render_topology_deck(project, optimization, mesh_index, density: np.ndarray) -> str:
    """Render one FEMaster topology sensitivity evaluation deck."""

    project.ensure_references(strict=True)
    analysis = project.try_resolve(optimization.analysis_ref)
    if analysis is None:
        raise ValueError("Topology optimization references a missing analysis")
    steps = tuple(getattr(analysis, "steps", ()) or ())
    if len(steps) != 1:
        raise ValueError(
            "Topology optimization currently requires exactly one analysis step"
        )
    step = steps[0]
    if step.step_type != "Linear Static":
        raise ValueError(
            "Topology optimization currently requires a Linear Static analysis"
        )

    values = np.asarray(density, dtype=float).ravel()
    if len(values) != mesh_index.count:
        raise ValueError(
            "The density vector does not match the exported element count"
        )

    writer = DeckWriter()
    context = ExportContext(project, analysis)
    writer.comment(
        "OpenCAE Studio generated FEMaster topology-optimization deck"
    )
    command(
        writer,
        "MODEL",
        NAME=context.solver_name(project, project.name),
    )

    instances = [
        item for item in project.assembly.instances if not item.suppressed
    ]
    if not instances:
        raise ValueError(
            "FEMaster topology export requires an active assembly instance"
        )
    node_offset = element_offset = 0
    exported = []
    context.options["region_aliases"] = {}
    context.options["entity_aliases"] = {}
    context.options["part_region_aliases"] = {}
    context.options["part_region_data"] = {}
    for instance in instances:
        part = project.try_resolve(instance.part_ref)
        if part is None:
            continue
        node_map, element_map, node_offset, element_offset = write_part_mesh(
            part,
            writer,
            context,
            instance,
            node_offset,
            element_offset,
        )
        exported.append((part, instance, node_map, element_map))

    if element_offset != mesh_index.count:
        raise ValueError(
            "Topology mesh manifest and FEMaster export disagree about the "
            f"element count ({mesh_index.count} vs {element_offset})"
        )

    node_offset = write_assembly_reference_points(
        project,
        writer,
        context,
        node_offset,
    )
    write_assembly_regions(project, exported, writer, context)
    for system in (
        *project.assembly.coordinate_systems,
        *(item for part in project.parts for item in part.coordinate_systems),
    ):
        write_orientation(system, writer, context)
    for material in project.materials:
        write_material(material, writer, context)
    for profile in project.profiles:
        write_profile(profile, writer, context)
    for field in project.fields:
        write_field(field, writer, context)

    command(
        writer,
        "FIELD",
        [
            (int(solver_id), float(value))
            for solver_id, value in zip(mesh_index.solver_ids, values)
        ],
        NAME=DENSITY_FIELD_NAME,
        TYPE="ELEMENT",
        COLS=1,
        FILL="NAN",
    )

    for part, instance, _node_map, _element_map in exported:
        prefix = _safe(instance.name if instance else part.name)
        for assignment in part.section_assignments:
            section = project.try_resolve(assignment.section_ref)
            if section is None:
                raise ValueError(
                    f"Section assignment {assignment.name!r} references "
                    "a missing section"
                )
            target = materialize_region(
                assignment.target,
                RegionProjection.ELEMENTS,
                writer,
                context,
                owner=assignment,
                proposed_name=f"{prefix}_{_safe(assignment.name)}",
                instance_id=instance.id,
                cache_key=(
                    "section-assignment",
                    instance.id,
                    assignment.id,
                ),
            ).name
            orientation = (
                project.try_resolve(assignment.orientation_ref)
                if assignment.orientation_ref
                else None
            )
            orientation_name = (
                context.solver_name(orientation, orientation.name)
                if orientation
                else None
            )
            write_section(
                section,
                target,
                orientation_name,
                writer,
                context,
            )

    for constraint in project.assembly.constraints:
        write_constraint(constraint, writer, context)
    for support in project.supports:
        write_support(support, writer, context)
    for load in project.loads:
        write_load(load, writer, context)

    _write_topology_loadcase(step, optimization, writer, context)
    return writer.text()


def _write_topology_loadcase(step, optimization, writer, context):
    command(
        writer,
        "LOADCASE",
        TYPE="LINEARSTATICTOPO",
        NAME=context.solver_name(step, f"{step.name}_TOPO"),
    )
    support_names = [
        context.solver_name(entity, entity.name)
        if entity
        else context.current_name(ref)
        for ref in step.support_refs
        for entity in [context.resolve(ref)]
    ]
    load_names = [
        context.solver_name(entity, entity.name)
        if entity
        else context.current_name(ref)
        for ref in step.load_refs
        for entity in [context.resolve(ref)]
    ]
    if support_names:
        command(
            writer,
            "SUPPORTS",
            [(name,) for name in support_names],
        )
    if step.uses_loads and load_names:
        command(writer, "LOADS", [(name,) for name in load_names])
    settings = step.settings
    command(
        writer,
        "SOLVER",
        DEVICE=settings.get("device", "CPU"),
        METHOD=settings.get("method", "DIRECT"),
    )
    command(
        writer,
        "CONSTRAINTMETHOD",
        TYPE=settings.get("constraint_method", "NULLSPACE"),
    )
    command(writer, "TOPODENSITY", FIELD=DENSITY_FIELD_NAME)
    command(
        writer,
        "TOPOEXPONENT",
        [(float(optimization.control_settings.simp_exponent),)],
    )
