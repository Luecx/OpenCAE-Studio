from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from opencae.core.ids import new_id
from ..core import DeckWriter, Entity, ExportContext, ProjectIndex, SolverName, register_model_type
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
    schema_version: int = 13
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
    _index: ProjectIndex | None = field(init=False, default=None, repr=False, compare=False)
    reference_errors: list[str] = field(init=False, default_factory=list, repr=False, compare=False)

    def __post_init__(self):
        known = {item.name for item in self.fields}
        for material in self.materials:
            for item in getattr(material, "fields", ()):
                if item.name not in known:
                    self.fields.append(item); known.add(item.name)
            if hasattr(material, "fields"): material.fields.clear()
        self._flatten_steps(); self.rebuild_index()

    def _flatten_steps(self):
        flattened = []
        for analysis in self.analyses:
            if len(analysis.steps) <= 1:
                flattened.append(analysis)
                continue
            for index, step in enumerate(analysis.steps):
                clone = deepcopy(analysis)
                if index:
                    object.__setattr__(clone, "id", new_id("entity"))
                clone.name = step.name
                clone.steps = [deepcopy(step)]
                flattened.append(clone)
        self.analyses = flattened


    @property
    def index(self) -> ProjectIndex:
        if self._index is None: self.rebuild_index()
        return self._index

    def rebuild_index(self, strict: bool = False) -> ProjectIndex:
        from ..core.reference_binding import bind_project_references
        initial = ProjectIndex(self)
        self.reference_errors = bind_project_references(self, initial, strict)
        self._index = ProjectIndex(self)
        return self._index

    def ensure_references(self, strict: bool = False) -> list[str]:
        self.rebuild_index(strict); return list(self.reference_errors)

    def resolve(self, ref, expected_type=None): return self.index.resolve(ref, expected_type)
    def try_resolve(self, ref, expected_type=None): return self.index.try_resolve(ref, expected_type)
    def references_to(self, entity_or_id):
        entity_id = getattr(entity_or_id, "id", entity_or_id); return self.index.references_to(str(entity_id))

    def render_deck(self, solver: SolverName | str, analysis: Analysis | None = None) -> str:
        self.ensure_references(strict=True)
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
