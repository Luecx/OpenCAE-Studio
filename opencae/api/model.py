"""Defines the single public model-authoring facade.

The :class:`Model` class owns user-facing orchestration only. Concrete creation
logic lives in focused ``model_*`` companion modules so this facade stays small
while preserving one discoverable API surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from opencae.model.core import Entity
from opencae.model.entities import (
    Assembly,
    ConcentratedLoad,
    CoordinateSystem,
    Element,
    Instance,
    Material,
    Node,
    Part,
    PressureLoad,
    Profile,
    Project,
    Region,
    Section,
)
from opencae.model.selection import RegionDefinition

from .model_assembly import create_coordinate_system, create_instance
from .model_loads import create_concentrated_load, create_pressure_load
from .model_mesh import create_element, create_node
from .model_ownership import require_owned
from .model_parts import create_part
from .model_regions import (
    create_element_set,
    create_node_set,
    create_region_target,
    create_surface,
)
from .model_resources import create_material, create_section


@dataclass
class Model:
    """High-level object API for constructing one OpenCAE project graph.

    Public callers work with Python objects. Stable IDs and ``EntityRef`` values
    remain implementation details of the domain/persistence layers.
    """

    project: Project

    @classmethod
    def create(
        cls,
        name: str = "Untitled",
        *,
        unit_system: str = "mm-N-s-°C",
    ) -> "Model":
        """Create an empty model backed by a new :class:`Project`."""
        return cls(Project(name=name, unit_system=unit_system))

    def _refresh(self) -> None:
        """Rebuild project identity/reference indexes after graph mutation."""
        # Authoring helpers mutate the aggregate directly for a compact API.
        # Rebuilding here keeps object aliases and ownership checks deterministic.
        self.project.rebuild_index()

    def _require_owned(
        self,
        entity: Entity,
        expected: type | tuple[type, ...],
    ) -> Entity:
        """Validate an object's type and identity within this model."""
        return require_owned(self, entity, expected)

    def part(self, name: str, *, source_type: str = "Manual") -> Part:
        """Create and attach a part to the project."""
        return create_part(self, name, source_type=source_type)

    def material(
        self,
        name: str,
        *,
        youngs_modulus: float | None = None,
        poisson_ratio: float | None = None,
        density: float | None = None,
    ) -> Material:
        """Create a material with common isotropic properties."""
        return create_material(
            self,
            name,
            youngs_modulus=youngs_modulus,
            poisson_ratio=poisson_ratio,
            density=density,
        )

    def section(
        self,
        name: str,
        *,
        material: Material | None = None,
        profile: Profile | None = None,
        section_type: str = "Solid",
        thickness: float = 0.0,
    ) -> Section:
        """Create a section referencing material/profile objects directly."""
        return create_section(
            self,
            name,
            material=material,
            profile=profile,
            section_type=section_type,
            thickness=thickness,
        )

    def instance(
        self,
        part: Part,
        *,
        name: str | None = None,
        translation=(0.0, 0.0, 0.0),
        rotation=(0.0, 0.0, 0.0),
    ) -> Instance:
        """Create an assembly occurrence of ``part``."""
        return create_instance(
            self,
            part,
            name=name,
            translation=translation,
            rotation=rotation,
        )

    def coordinate_system(
        self,
        owner: Part | Assembly,
        *,
        name: str,
        origin=(0.0, 0.0, 0.0),
        axis_1=(1.0, 0.0, 0.0),
        axis_2=(0.0, 1.0, 0.0),
        system_type: str = "Cartesian",
    ) -> CoordinateSystem:
        """Create a part- or assembly-scoped coordinate system."""
        return create_coordinate_system(
            self,
            owner,
            name=name,
            origin=origin,
            axis_1=axis_1,
            axis_2=axis_2,
            system_type=system_type,
        )

    def node(
        self,
        part: Part,
        coordinates: tuple[float, float, float],
        *,
        node_id: int | None = None,
    ) -> Node:
        """Create one authored finite-element node in ``part``."""
        return create_node(self, part, coordinates, node_id=node_id)

    def element(
        self,
        part: Part,
        element_type: type[Element],
        nodes: Iterable[Node],
        *,
        element_id: int | None = None,
    ) -> Element:
        """Create one authored finite element from Node objects."""
        return create_element(
            self,
            part,
            element_type,
            nodes,
            element_id=element_id,
        )

    def node_set(
        self,
        part: Part,
        name: str,
        nodes: Iterable[Node],
    ) -> Region:
        """Create a named part region from authored Node objects."""
        return create_node_set(self, part, name, nodes)

    def element_set(
        self,
        part: Part,
        name: str,
        elements: Iterable[Element],
    ) -> Region:
        """Create a named part region from authored Element objects."""
        return create_element_set(self, part, name, elements)

    def surface(
        self,
        part: Part,
        name: str,
        facets: Iterable[tuple[Element, str]],
    ) -> Region:
        """Create a named surface from ``(element, local_face)`` pairs."""
        return create_surface(self, part, name, facets)

    def region_target(
        self,
        region: Region,
        *,
        instance: Instance | None = None,
    ) -> RegionDefinition:
        """Project a named Region object into solver/selection target space."""
        return create_region_target(self, region, instance=instance)

    def concentrated_load(
        self,
        name: str,
        *,
        target: Region,
        components: Iterable[float],
        coordinate_system: CoordinateSystem | None = None,
        instance: Instance | None = None,
    ) -> ConcentratedLoad:
        """Create a six-component concentrated load on a Region object."""
        return create_concentrated_load(
            self,
            name,
            target=target,
            components=components,
            coordinate_system=coordinate_system,
            instance=instance,
        )

    def pressure_load(
        self,
        name: str,
        *,
        target: Region,
        pressure: float,
        instance: Instance | None = None,
    ) -> PressureLoad:
        """Create a pressure load on a Region object."""
        return create_pressure_load(
            self,
            name,
            target=target,
            pressure=pressure,
            instance=instance,
        )

    def validate(self) -> None:
        """Raise if the authored project contains invalid references."""
        self.project.ensure_references(strict=True)
