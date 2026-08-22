from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from opencae.model.core import Entity, EntityRef
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
from opencae.model.entities.resources.material_behaviors import (
    DensityBehavior,
    IsotropicElasticity,
)
from opencae.model.selection import (
    MeshElementOperand,
    MeshFacetOperand,
    MeshNodeOperand,
    NamedRegionOperand,
    RegionDefinition,
    RegionProjection,
    RegionScope,
)


@dataclass
class Model:
    """High-level object API for constructing OpenCAE models.

    Public callers work with Python objects. Stable ids and ``EntityRef`` are
    persistence details created by this facade, never string-based user input.
    """

    project: Project

    @classmethod
    def create(
        cls,
        name: str = "Untitled",
        *,
        unit_system: str = "mm-N-s-°C",
    ) -> "Model":
        return cls(Project(name=name, unit_system=unit_system))

    def _refresh(self) -> None:
        self.project.rebuild_index()

    def _require_owned(self, entity: Entity, expected: type | tuple[type, ...]):
        if not isinstance(entity, expected):
            names = (
                ", ".join(item.__name__ for item in expected)
                if isinstance(expected, tuple)
                else expected.__name__
            )
            raise TypeError(f"Expected {names}, got {type(entity).__name__}")
        if entity is self.project:
            return entity
        if self.project.try_resolve(entity.id) is not entity:
            raise ValueError(
                f"{type(entity).__name__} '{entity.name}' does not belong "
                "to this Model"
            )
        return entity

    def part(self, name: str, *, source_type: str = "Manual") -> Part:
        part = Part(name=name, source_type=source_type)
        self.project.parts.append(part)
        self._refresh()
        return part

    def material(
        self,
        name: str,
        *,
        youngs_modulus: float | None = None,
        poisson_ratio: float | None = None,
        density: float | None = None,
    ) -> Material:
        behaviors = []
        if youngs_modulus is not None or poisson_ratio is not None:
            if youngs_modulus is None or poisson_ratio is None:
                raise ValueError(
                    "youngs_modulus and poisson_ratio must be supplied together"
                )
            behaviors.append(
                IsotropicElasticity(
                    youngs_modulus=float(youngs_modulus),
                    poisson_ratio=float(poisson_ratio),
                )
            )
        if density is not None:
            behaviors.append(DensityBehavior(value=float(density)))
        material = Material(name=name, behaviors=behaviors)
        self.project.materials.append(material)
        self._refresh()
        return material

    def section(
        self,
        name: str,
        *,
        material: Material | None = None,
        profile: Profile | None = None,
        section_type: str = "Solid",
        thickness: float = 0.0,
    ) -> Section:
        if material is not None:
            self._require_owned(material, Material)
        if profile is not None:
            self._require_owned(profile, Profile)
        section = Section(
            name=name,
            section_type=section_type,
            thickness=float(thickness),
        )
        section.material = material
        section.profile = profile
        self.project.sections.append(section)
        self._refresh()
        return section

    def instance(
        self,
        part: Part,
        *,
        name: str | None = None,
        translation=(0.0, 0.0, 0.0),
        rotation=(0.0, 0.0, 0.0),
    ) -> Instance:
        self._require_owned(part, Part)
        instance = Instance(
            name=name or f"{part.name}-1",
            translation=tuple(float(v) for v in translation),
            rotation=tuple(float(v) for v in rotation),
        )
        instance.part = part
        self.project.assembly.instances.append(instance)
        self._refresh()
        return instance

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
        self._require_owned(owner, (Part, Assembly))
        scope = "Part" if isinstance(owner, Part) else "Assembly"
        csys = CoordinateSystem(
            name=name,
            system_type=system_type,
            origin=tuple(float(v) for v in origin),
            axis_1=tuple(float(v) for v in axis_1),
            axis_2=tuple(float(v) for v in axis_2),
            scope=scope,
        )
        owner.coordinate_systems.append(csys)
        self._refresh()
        return csys

    def node(
        self,
        part: Part,
        coordinates: tuple[float, float, float],
        *,
        node_id: int | None = None,
    ) -> Node:
        self._require_owned(part, Part)
        return part.mesh.add_node(coordinates, node_id)

    def element(
        self,
        part: Part,
        element_type: type[Element],
        nodes: Iterable[Node],
        *,
        element_id: int | None = None,
    ) -> Element:
        self._require_owned(part, Part)
        return part.mesh.add_element(element_type, tuple(nodes), element_id)

    def node_set(
        self,
        part: Part,
        name: str,
        nodes: Iterable[Node],
    ) -> Region:
        self._require_owned(part, Part)
        operands = tuple(
            MeshNodeOperand(
                owner_ref=EntityRef.of(part, "Part"),
                node_id=node.id,
                mesh_revision=part.mesh.revision,
            )
            for node in nodes
        )
        region = Region(
            name=name,
            scope=RegionScope.PART,
            preferred_projection=RegionProjection.NODES,
            definition=RegionDefinition.from_values(operands),
            geometry_backed=False,
        )
        part.regions.append(region)
        self._refresh()
        return region

    def element_set(
        self,
        part: Part,
        name: str,
        elements: Iterable[Element],
    ) -> Region:
        self._require_owned(part, Part)
        operands = tuple(
            MeshElementOperand(
                owner_ref=EntityRef.of(part, "Part"),
                element_id=element.id,
                mesh_revision=part.mesh.revision,
            )
            for element in elements
        )
        region = Region(
            name=name,
            scope=RegionScope.PART,
            preferred_projection=RegionProjection.ELEMENTS,
            definition=RegionDefinition.from_values(operands),
            geometry_backed=False,
        )
        part.regions.append(region)
        self._refresh()
        return region

    def surface(
        self,
        part: Part,
        name: str,
        facets: Iterable[tuple[Element, str]],
    ) -> Region:
        self._require_owned(part, Part)
        operands = tuple(
            MeshFacetOperand(
                owner_ref=EntityRef.of(part, "Part"),
                element_id=element.id,
                local_face=str(local_face),
                mesh_revision=part.mesh.revision,
            )
            for element, local_face in facets
        )
        region = Region(
            name=name,
            scope=RegionScope.PART,
            preferred_projection=RegionProjection.FACETS,
            definition=RegionDefinition.from_values(operands),
            geometry_backed=False,
        )
        part.regions.append(region)
        self._refresh()
        return region

    def region_target(
        self,
        region: Region,
        *,
        instance: Instance | None = None,
    ) -> RegionDefinition:
        """Create a solver/selection target from a Region object.

        Part regions need an occurrence in assembly space. If the part has a
        single active instance it is selected automatically; otherwise callers
        pass the desired Instance object explicitly.
        """
        self._require_owned(region, Region)
        instance_ref = None
        if region.scope == RegionScope.PART:
            parent_id = self.project.index.parent_id.get(region.id)
            part = self.project.try_resolve(parent_id, Part)
            if part is None:
                raise ValueError(f"Part region '{region.name}' has no owning Part")
            if instance is None:
                candidates = [
                    item
                    for item in self.project.assembly.instances
                    if not item.suppressed and item.part is part
                ]
                if len(candidates) != 1:
                    raise ValueError(
                        f"Part region '{region.name}' requires an Instance; "
                        f"found {len(candidates)} active occurrences"
                    )
                instance = candidates[0]
            self._require_owned(instance, Instance)
            if instance.part is not part:
                raise ValueError(
                    f"Instance '{instance.name}' does not instantiate "
                    f"Part '{part.name}'"
                )
            instance_ref = EntityRef.of(instance, "Instance")
        return RegionDefinition.from_values(
            (
                NamedRegionOperand(
                    region_ref=EntityRef.of(region, "Region"),
                    instance_ref=instance_ref,
                ),
            )
        )

    def concentrated_load(
        self,
        name: str,
        *,
        target: Region,
        components: Iterable[float],
        coordinate_system: CoordinateSystem | None = None,
        instance: Instance | None = None,
    ) -> ConcentratedLoad:
        self._require_owned(target, Region)
        if coordinate_system is not None:
            self._require_owned(coordinate_system, CoordinateSystem)
        values = [float(value) for value in components]
        if len(values) != 6:
            raise ValueError("A concentrated load requires six components")
        load = ConcentratedLoad(
            name=name,
            target=self.region_target(target, instance=instance),
            components=values,
        )
        load.coordinate_system = coordinate_system
        self.project.loads.append(load)
        self._refresh()
        return load

    def pressure_load(
        self,
        name: str,
        *,
        target: Region,
        pressure: float,
        instance: Instance | None = None,
    ) -> PressureLoad:
        self._require_owned(target, Region)
        load = PressureLoad(
            name=name,
            target=self.region_target(target, instance=instance),
            pressure=float(pressure),
        )
        self.project.loads.append(load)
        self._refresh()
        return load

    def validate(self) -> None:
        self.project.ensure_references(strict=True)
