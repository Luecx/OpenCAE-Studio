"""Provides application-level solver export for complete Project aggregates.

Domain entities know how to emit their local solver records, but Project-level
ordering, headings, and solver adapter selection belong here rather than inside
the persistent Project model.
"""

from __future__ import annotations

from opencae.model.core import DeckWriter, ExportContext, SolverName


def render_deck(project, solver: SolverName | str, analysis=None) -> str:
    """Validate ``project`` and render a complete solver deck as text."""
    project.ensure_references(strict=True)
    solver_name = SolverName(solver)
    writer = DeckWriter()
    context = ExportContext(project, analysis)
    write_project(project, solver_name, writer, context)
    return writer.text()


def write_project(project, solver, writer, context) -> None:
    """Write a complete Project into an existing DeckWriter/ExportContext."""
    solver_name = SolverName(solver)
    if solver_name is SolverName.FEMASTER:
        from opencae.solvers.femaster_dsl.emitters import write_project as emit

        writer.comment("OpenCAE Studio generated FEMaster deck")
        emit(project, writer, context)
        return

    if solver_name is SolverName.ABAQUS:
        writer.comment("OpenCAE Studio generated Abaqus deck")
        writer.line("*HEADING")
        writer.line(project.name)
    else:
        writer.comment(f"OpenCAE generic deck for {project.name}")

    write_project_contents(project, solver_name, writer, context)


def write_project_contents(project, solver, writer, context) -> None:
    """Emit solver-writable entities in canonical Project dependency order."""
    # Resources precede Parts so every section/material name exists before a
    # downstream solver references it.
    for entity in (
        *project.materials,
        *project.profiles,
        *project.sections,
        *project.fields,
        *project.parts,
    ):
        entity.write_solver(solver, writer, context)

    project.assembly.write_solver(solver, writer, context)
    for entity in (*project.supports, *project.loads):
        entity.write_solver(solver, writer, context)

    # A selected Analysis produces a focused deck; otherwise generic export can
    # include all definitions in persistent order.
    if context.analysis:
        context.analysis.write_solver(solver, writer, context)
    else:
        for analysis in project.analyses:
            analysis.write_solver(solver, writer, context)
