"""Defines the persistent root aggregate of one OpenCAE model.

Project owns domain collections and reference navigation only. Graph-shape
compatibility is delegated to ``project_migrations`` and solver export ordering
to ``opencae.exporting``.
"""

from dataclasses import dataclass, field
from pathlib import Path

from ..core import Entity, ProjectIndex, SolverName, register_model_type
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
    """Persistent aggregate root for model definition, execution, and results."""

    schema_version: int = 21
    name: str = "Untitled"
    unit_system: str = "mm-N-s-°C"
    path: Path | None = None
    parts: list[Part] = field(default_factory=list)
    assembly: Assembly = field(
        default_factory=lambda: Assembly(name="Main Assembly")
    )
    supports: list[Support] = field(default_factory=list)
    loads: list[Load] = field(default_factory=list)
    materials: list[Material] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    profiles: list[Profile] = field(default_factory=list)
    fields: list[FieldDefinition] = field(default_factory=list)
    steps: list[AnalysisStep] = field(default_factory=list)
    analyses: list[Analysis] = field(default_factory=list)
    studies: list[Study] = field(default_factory=list)
    # Legacy import field. ``project_migrations`` aliases this to ``studies`` and
    # serialization omits it so new files keep one canonical collection.
    optimizations: list[TopologyOptimization] = field(
        default_factory=list,
        metadata={"serialize": False},
    )
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
        """Normalize legacy graph shapes and build the identity/reference index."""
        from .project_migrations import migrate_project_graph

        # Direct Project construction is part of the Python model API, so graph
        # compatibility must also hold outside file-loading code.
        migrate_project_graph(self)
        self.rebuild_index()

    @property
    def index(self) -> ProjectIndex:
        """Return the current ProjectIndex, rebuilding lazily when absent."""
        if self._index is None:
            self.rebuild_index()
        return self._index

    def rebuild_index(self, strict: bool = False) -> ProjectIndex:
        """Rebuild entity identity/reverse references and validate the graph."""
        from ..core.reference_binding import validate_project_references

        self._index = ProjectIndex(self)
        self.reference_errors = validate_project_references(
            self,
            self._index,
            strict,
        )
        return self._index

    def ensure_references(self, strict: bool = False) -> list[str]:
        """Refresh reference diagnostics and optionally raise on invalid links."""
        self.rebuild_index(strict)
        return list(self.reference_errors)

    def resolve(self, ref, expected_type=None):
        """Resolve one stable entity reference and optionally enforce its type."""
        return self.index.resolve(ref, expected_type)

    def try_resolve(self, ref, expected_type=None):
        """Resolve one reference or return ``None`` when it is unavailable."""
        return self.index.try_resolve(ref, expected_type)

    def references_to(self, entity_or_id):
        """Return reverse-reference uses targeting an entity object or ID."""
        entity_id = getattr(entity_or_id, "id", entity_or_id)
        return self.index.references_to(str(entity_id))

    def render_deck(
        self,
        solver: SolverName | str,
        analysis: Analysis | None = None,
    ) -> str:
        """Render this Project through the application-level export service."""
        from opencae.exporting import render_deck

        return render_deck(self, solver, analysis)

    def write_abaqus(self, writer, context) -> None:
        """Delegate complete Abaqus Project export to the export service."""
        from opencae.exporting import write_project

        write_project(self, SolverName.ABAQUS, writer, context)

    def write_femaster(self, writer, context) -> None:
        """Delegate complete FEMaster Project export to the export service."""
        from opencae.exporting import write_project

        write_project(self, SolverName.FEMASTER, writer, context)

    def write_generic(self, writer, context) -> None:
        """Delegate complete generic Project export to the export service."""
        from opencae.exporting import write_project

        write_project(self, SolverName.GENERIC, writer, context)
