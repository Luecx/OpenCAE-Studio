from __future__ import annotations

from opencae.model.core import DeckWriter, ExportContext, SolverName


def render_deck(project, solver: SolverName | str, analysis=None) -> str:
    """Application-level export entry point.

    Domain entities no longer import solver implementations. Export adapters
    consume the domain graph from the outside.
    """
    project.ensure_references(strict=True)
    solver = SolverName(solver)
    writer = DeckWriter()
    context = ExportContext(project, analysis)
    if solver is SolverName.FEMASTER:
        from opencae.solvers.femaster_dsl.emitters import write_project
        writer.comment("OpenCAE Studio generated FEMaster deck")
        write_project(project, writer, context)
    elif solver is SolverName.ABAQUS:
        writer.comment("OpenCAE Studio generated Abaqus deck")
        writer.line("*HEADING")
        writer.line(project.name)
        project._write_contents(SolverName.ABAQUS, writer, context)
    else:
        writer.comment(f"OpenCAE generic deck for {project.name}")
        project._write_contents(SolverName.GENERIC, writer, context)
    return writer.text()
