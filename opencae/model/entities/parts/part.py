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


@register_model_type("part")
@dataclass
class Part(Entity):
    source_type: str = "CAD"
    geometry_settings: GeometrySettings = field(default_factory=GeometrySettings)
    geometry: list[GeometryFeature] = field(default_factory=list)
    mesh: MeshState = field(default_factory=MeshState)
    node_sets: list[Region] = field(default_factory=list)
    element_sets: list[Region] = field(default_factory=list)
    surfaces: list[Region] = field(default_factory=list)
    coordinate_systems: list[CoordinateSystem] = field(default_factory=list)
    reference_points: list[ReferencePoint] = field(default_factory=list)
    datums: list[Datum] = field(default_factory=list)
    orientations: list[Orientation] = field(default_factory=list)
    section_assignments: list[SectionAssignment] = field(default_factory=list)

    def write_abaqus(self, writer, context) -> None:
        writer.line(f"*PART, NAME={self.name}")
        for region in (*self.node_sets, *self.element_sets, *self.surfaces):
            region.write_abaqus(writer, context)
        for assignment in self.section_assignments:
            assignment.write_abaqus(writer, context)
        writer.line("*END PART")

    def write_femaster(self, writer, context) -> None:
        from opencae.solvers.femaster_dsl.emitters.mesh import write_part_mesh
        write_part_mesh(self, writer, context)
