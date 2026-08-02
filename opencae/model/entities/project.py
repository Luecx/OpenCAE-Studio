from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from ..core import DeckWriter, Entity, ExportContext, SolverName, register_model_type
from .analysis.analysis import Analysis
from .assembly.assembly import Assembly
from .jobs.job import Job
from .jobs.result_set import ResultSet
from .loads.base import Load
from .parts.part import Part
from .profiles.base import Profile
from .resources.material import Material
from .fields import FieldDefinition
from .sections.base import Section
from .supports.base import Support


@register_model_type("project")
@dataclass
class Project(Entity):
    name: str = "Untitled"
    unit_system: str = "mm-N-s-°C"
    path: Path | None = None
    parts: list[Part] = field(default_factory=list)
    assembly: Assembly = field(default_factory=lambda: Assembly(name="Main Assembly"))
    supports: list[Support] = field(default_factory=list)
    loads: list[Load] = field(default_factory=list)
    materials: list[Material] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    profiles: list[Profile] = field(default_factory=list)
    fields: list[FieldDefinition] = field(default_factory=list)
    analyses: list[Analysis] = field(default_factory=list)
    jobs: list[Job] = field(default_factory=list)
    results: list[ResultSet] = field(default_factory=list)

    def __post_init__(self):
        known = {item.name for item in self.fields}
        for material in self.materials:
            for item in getattr(material, "fields", ()):
                if item.name not in known:
                    self.fields.append(item); known.add(item.name)
            if hasattr(material, "fields"): material.fields.clear()
        self._flatten_steps()

    def _flatten_steps(self):
        flattened=[]
        for analysis in self.analyses:
            if len(analysis.steps)<=1:
                flattened.append(analysis); continue
            for step in analysis.steps:
                clone=deepcopy(analysis); clone.name=step.name; clone.steps=[step]; flattened.append(clone)
        self.analyses=flattened

    def render_deck(self, solver: SolverName | str, analysis: Analysis | None = None) -> str:
        writer = DeckWriter()
        context = ExportContext(self, analysis)
        self.write_solver(solver, writer, context)
        return writer.text()

    def write_abaqus(self, writer, context) -> None:
        writer.comment("OpenCAE Studio generated Abaqus deck")
        writer.line("*HEADING")
        writer.line(self.name)
        self._write_contents(SolverName.ABAQUS, writer, context)

    def write_femaster(self, writer, context) -> None:
        from opencae.solvers.femaster_dsl.emitters import write_project
        writer.comment("OpenCAE Studio generated FEMaster deck")
        write_project(self, writer, context)

    def write_generic(self, writer, context) -> None:
        writer.comment(f"OpenCAE generic deck for {self.name}")
        self._write_contents(SolverName.GENERIC, writer, context)

    def _write_contents(self, solver, writer, context) -> None:
        for entity in (*self.materials, *self.profiles, *self.sections, *self.fields, *self.parts):
            entity.write_solver(solver, writer, context)
        self.assembly.write_solver(solver, writer, context)
        for entity in (*self.supports, *self.loads):
            entity.write_solver(solver, writer, context)
        if context.analysis:
            context.analysis.write_solver(solver, writer, context)
        else:
            for analysis in self.analyses:analysis.write_solver(solver,writer,context)
