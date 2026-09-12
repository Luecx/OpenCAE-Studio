"""Defines the persistent root aggregate of one OpenCAE model.

Project owns the current domain graph and reference navigation. File-format
versioning, migrations, and filesystem state are persistence/application
responsibilities and are deliberately kept out of the aggregate.
"""

from dataclasses import dataclass, field
from pathlib import Path

from ..core import Entity, ProjectIndex, SolverName, register_model_type
from .amplitudes import Amplitude
from .analysis.analysis import Analysis
from .analysis.step import AnalysisStep
from .assembly.assembly import Assembly
from .fields import FieldDefinition
from .jobs.job import Job
from .jobs.result_set import ResultSet
from .loads.base import Load
from .parts.part import Part
from .profiles.base import Profile
from .resources.material import Material
from .sections.base import Section
from .studies import Study
from .supports.base import Support


@register_model_type("project")
@dataclass
class Project(Entity):
    """Current OpenCAE model aggregate with one canonical owner per entity."""

    name: str = "Untitled"
    unit_system: str = "mm-N-s-°C"
    path: Path | None = field(
        default=None,
        metadata={"serialize": False},
    )
    parts: list[Part] = field(default_factory=list)
    assembly: Assembly = field(
        default_factory=lambda: Assembly(name="Main Assembly")
    )
    supports: list[Support] = field(default_factory=list)
    loads: list[Load] = field(default_factory=list)
    amplitudes: list[Amplitude] = field(default_factory=list)
    materials: list[Material] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    profiles: list[Profile] = field(default_factory=list)
    fields: list[FieldDefinition] = field(default_factory=list)
    steps: list[AnalysisStep] = field(default_factory=list)
    analyses: list[Analysis] = field(default_factory=list)
    studies: list[Study] = field(default_factory=list)
    jobs: list[Job] = field(default_factory=list)
    results: list[ResultSet] = field(default_factory=list)
    _index: ProjectIndex | None = field(
        init=False,
        default=None,
        repr=False,
        compare=False,
    )
    reference_errors: list[str] = field(
        init=False,
        default_factory=list,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        self.rebuild_index()

    @property
    def index(self) -> ProjectIndex:
        if self._index is None:
            self.rebuild_index()
        return self._index

    def invalidate_index(self) -> None:
        self._index = None

    def rebuild_index(self, strict: bool = False) -> ProjectIndex:
        """Bind wire references, rebuild identity/reverse indexes and validate."""
        from ..core.reference_binding import (
            bind_project_object_references,
            validate_project_references,
        )

        index = ProjectIndex(self)
        if bind_project_object_references(self, index):
            # The first pass indexes ownership while decoded relationship fields
            # may still contain EntityRef/mesh-ID wire values. Rebuild once after
            # binding so reverse references always describe canonical objects.
            index = ProjectIndex(self)
        self._index = index
        self.reference_errors = validate_project_references(
            self,
            self._index,
            strict,
        )
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

    def render_deck(
        self,
        solver: SolverName | str,
        analysis: Analysis | None = None,
    ) -> str:
        from opencae.exporting import render_deck

        return render_deck(self, solver, analysis)

    def write_abaqus(self, writer, context) -> None:
        from opencae.exporting import write_project

        write_project(self, SolverName.ABAQUS, writer, context)

    def write_femaster(self, writer, context) -> None:
        from opencae.exporting import write_project

        write_project(self, SolverName.FEMASTER, writer, context)

    def write_generic(self, writer, context) -> None:
        from opencae.exporting import write_project

        write_project(self, SolverName.GENERIC, writer, context)
