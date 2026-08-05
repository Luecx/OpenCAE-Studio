"""Defines the persistent OpenCAE project aggregate and migration hooks."""

from dataclasses import dataclass, field
from pathlib import Path

from ..core import DeckWriter, Entity, ExportContext, ProjectIndex, SolverName, register_model_type
from .analysis.analysis import Analysis
from .analysis.step import AnalysisStep
from .assembly.assembly import Assembly
from .fields import FieldDefinition
from .jobs.job import Job
from .jobs.result_set import ResultSet
from .loads.base import Load
from .optimization import TopologyOptimization
from .parts.part import Part
from .profiles.base import Profile
from .resources.material import Material
from .sections.base import Section
from .studies import Study
from .supports.base import Support


@register_model_type("project")
@dataclass
class Project(Entity):
    schema_version: int = 21
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
    steps: list[AnalysisStep] = field(default_factory=list)
    analyses: list[Analysis] = field(default_factory=list)
    studies: list[Study] = field(default_factory=list)
    # Legacy import field. It is rebound to studies in __post_init__ and is not
    # written again, so new project files have one canonical study collection.
    optimizations: list[TopologyOptimization] = field(
        default_factory=list,
        metadata={"serialize": False},
    )
    jobs: list[Job] = field(default_factory=list)
    results: list[ResultSet] = field(default_factory=list)
    _index: ProjectIndex | None = field(init=False, default=None, repr=False, compare=False)
    reference_errors: list[str] = field(init=False, default_factory=list, repr=False, compare=False)

    def __post_init__(self):
        known = {item.name for item in self.fields}
        for material in self.materials:
            for item in getattr(material, "fields", ()):
                if item.name not in known:
                    self.fields.append(item)
                    known.add(item.name)
            if hasattr(material, "fields"):
                material.fields.clear()
        self._migrate_shared_steps()
        self._migrate_studies()
        self.rebuild_index()

    def _migrate_shared_steps(self):
        """Move legacy analysis-owned steps into the project-level collection."""

        by_id = {step.id: step for step in self.steps}
        for analysis in self.analyses:
            if not analysis.step_refs:
                ordered = []
                for step in tuple(analysis.steps):
                    stored = by_id.get(step.id)
                    if stored is None:
                        self.steps.append(step)
                        by_id[step.id] = step
                        stored = step
                    ordered.append(stored)
                if ordered:
                    analysis.bind_steps(ordered)
            analysis.steps = []

    def _migrate_studies(self):
        """Import the former optimizations collection and expose a live alias."""

        known = {item.id for item in self.studies}
        for study in tuple(self.optimizations):
            if study.id not in known:
                self.studies.append(study)
                known.add(study.id)
        self.optimizations = self.studies

    @property
    def index(self) -> ProjectIndex:
        if self._index is None:
            self.rebuild_index()
        return self._index

    def rebuild_index(self, strict: bool = False) -> ProjectIndex:
        from ..core.reference_binding import validate_project_references

        self._index = ProjectIndex(self)
        self.reference_errors = validate_project_references(self, self._index, strict)
        return self._index

    def ensure_references(self, strict: bool = False) -> list[str]:
        self.rebuild_index(strict)
        return list(self.reference_errors)

    def resolve(self, ref, expected_type=None):
        return self.index.resolve(ref, expected_type)

    def try_resolve(self, ref, expected_type=None):
        return self.index.try_resolve(ref, expected_type)

    def references_to(self, entity_or_id):
        entity_id = getattr(entity_or_id, "id", entity_or_id)
        return self.index.references_to(str(entity_id))

    def render_deck(self, solver: SolverName | str, analysis: Analysis | None = None) -> str:
        from opencae.exporting import render_deck

        return render_deck(self, solver, analysis)

    def write_abaqus(self, writer, context) -> None:
        writer.comment("OpenCAE Studio generated Abaqus deck")
        writer.line("*HEADING")
        writer.line(self.name)
        self._write_contents(SolverName.ABAQUS, writer, context)

    def write_femaster(self, writer, context) -> None:
        raise RuntimeError("Use opencae.exporting.render_deck for FEMaster export")

    def write_generic(self, writer, context) -> None:
        writer.comment(f"OpenCAE generic deck for {self.name}")
        self._write_contents(SolverName.GENERIC, writer, context)

    def _write_contents(self, solver, writer, context) -> None:
        for entity in (
            *self.materials,
            *self.profiles,
            *self.sections,
            *self.fields,
            *self.parts,
        ):
            entity.write_solver(solver, writer, context)
        self.assembly.write_solver(solver, writer, context)
        for entity in (*self.supports, *self.loads):
            entity.write_solver(solver, writer, context)
        if context.analysis:
            context.analysis.write_solver(solver, writer, context)
        else:
            for analysis in self.analyses:
                analysis.write_solver(solver, writer, context)
