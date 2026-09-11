"""Defines the Part aggregate and its owned geometry and mesh resources."""

from dataclasses import dataclass, field

from ...core import Entity, register_model_type
from ..geometry.feature import GeometryFeature
from ..geometry.geometry_settings import GeometrySettings
from ..mesh.mesh_state import MeshState
from ..regions.coordinate_system import CoordinateSystem
from ..regions.orientation import Orientation
from ..regions.reference_point import ReferencePoint
from ..regions.region import Region
from ..regions.section_assignment import SectionAssignment
from ..datums import Datum
from .part_source_kind import PartSourceKind


@register_model_type("part")
@dataclass
class Part(Entity):
    """Own geometry, mesh, regions, and assignments for one model Part."""

    source_type: PartSourceKind | str = PartSourceKind.MANUAL
    geometry_settings: GeometrySettings = field(default_factory=GeometrySettings)
    geometry: list[GeometryFeature] = field(default_factory=list)
    mesh: MeshState = field(default_factory=MeshState)
    regions: list[Region] = field(default_factory=list)
    coordinate_systems: list[CoordinateSystem] = field(default_factory=list)
    reference_points: list[ReferencePoint] = field(default_factory=list)
    datums: list[Datum] = field(default_factory=list)
    orientations: list[Orientation] = field(default_factory=list)
    section_assignments: list[SectionAssignment] = field(default_factory=list)

    def __setattr__(self, name, value) -> None:
        """Keep the Part origin canonical across construction and mutation."""
        if name == "source_type":
            value = PartSourceKind.coerce(value)
        super().__setattr__(name, value)

    def write_abaqus(self, writer, context) -> None:
        """Write the Part-owned Abaqus records through the legacy domain hook."""
        writer.line(f"*PART, NAME={self.name}")
        for region in self.regions:
            region.write_abaqus(writer, context)
        for assignment in self.section_assignments:
            assignment.write_abaqus(writer, context)
        writer.line("*END PART")

    def write_femaster(self, writer, context) -> None:
        """Defer FEMaster Part output to its dedicated project emitter."""
        return None
