"""Project-wide region, Step, Analysis and Job validation."""

from __future__ import annotations

from opencae.geometry.section_filter import region_families
from opencae.model.core.reference_binding import validate_region_consumers
from opencae.model.entities.analysis import AnalysisStep
from opencae.model.entities.jobs import Job
from opencae.model.entities.loads import TemperatureLoad
from opencae.model.selection import (
    RegionProjection,
    RegionRequirement,
    validate_region_definition,
)


def section_assignment_errors(project):
    """Return section-assignment diagnostics for the current Project graph."""
    project.ensure_references(False)
    return _section_assignment_errors(project)


def _section_assignment_errors(project):
    """Validate section assignments without rebuilding references again."""
    errors = []
    for part in project.parts:
        for assignment in part.section_assignments:
            section = project.try_resolve(assignment.section_ref)
            if section is None:
                errors.append(
                    f"{part.name}/{assignment.name}: referenced section does not exist"
                )
                continue
            diagnostics = validate_region_definition(
                project,
                assignment.target,
                RegionRequirement(
                    RegionProjection.ELEMENTS,
                    (1, 2, 3),
                    1,
                ),
                allow_part_local=True,
            )
            errors.extend(
                f"{part.name}/{assignment.name}: {item.message}"
                for item in diagnostics
                if item.severity == "error"
            )
            families = region_families(project, part, assignment.target)
            if families and section.section_type not in families:
                actual = ", ".join(sorted(families))
                errors.append(
                    f"{part.name}/{assignment.name}: {section.section_type} "
                    f"section cannot be assigned to {actual} elements"
                )
    return _unique(errors)


def validate_section_assignments(project):
    """Raise when any section assignment is invalid."""
    errors = section_assignment_errors(project)
    if errors:
        raise ValueError("Invalid section assignments:\n" + "\n".join(errors))


def validate_project(project, analysis=None):
    """Validate the project or the workflow relevant to one selected Analysis.

    Stable EntityRef validation is intentionally lightweight and maintained by
    ProjectIndex. Mesh-backed region semantics are evaluated here, at an explicit
    validation boundary, rather than on every unrelated undoable edit.
    """
    project.ensure_references(False)
    errors = list(project.reference_errors)
    errors.extend(validate_region_consumers(project))
    errors.extend(_section_assignment_errors(project))
    errors.extend(_region_consumer_errors(project))
    errors.extend(_workflow_errors(project, analysis))
    return _unique(errors)


def _region_consumer_errors(project):
    """Return non-region semantic errors for region-consuming entities."""
    errors = []
    for load in project.loads:
        if isinstance(load, TemperatureLoad):
            if (
                load.temperature_field_ref is None
                or project.try_resolve(load.temperature_field_ref) is None
            ):
                errors.append(f"{load.name}: temperature field is missing")
    return errors


def _workflow_errors(project, analysis=None):
    """Return Step, Analysis, Job and Result workflow consistency errors."""
    errors = []
    analyses = (analysis,) if analysis is not None else tuple(project.analyses)
    if analysis is not None:
        steps = tuple(analysis.resolved_steps(project))
    else:
        steps = tuple(project.steps)
    for step in steps:
        if not isinstance(step, AnalysisStep):
            errors.append("Project Steps contains an invalid entity")
            continue
        for ref in step.load_refs:
            if project.try_resolve(ref) not in project.loads:
                errors.append(f"{step.name}: referenced load does not exist")
        for ref in step.support_refs:
            if project.try_resolve(ref) not in project.supports:
                errors.append(f"{step.name}: referenced support does not exist")
    for selected in analyses:
        resolved = selected.resolved_steps(project)
        if not resolved:
            errors.append(f"{selected.name}: no valid Steps are referenced")
        for ref in selected.step_refs:
            if not isinstance(project.try_resolve(ref), AnalysisStep):
                errors.append(
                    f"{selected.name}: referenced Step does not exist"
                )
    if analysis is None:
        for job in project.jobs:
            if not isinstance(job, Job):
                continue
            if job.source_ref and project.try_resolve(job.source_ref) is None:
                errors.append(f"{job.name}: referenced source does not exist")
        for result in project.results:
            if not result.job_ref or not isinstance(
                project.try_resolve(result.job_ref),
                Job,
            ):
                errors.append(f"{result.name}: generating Job does not exist")
    return errors


def _unique(values):
    """Return input diagnostics in stable order without duplicates."""
    result = []
    seen = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
