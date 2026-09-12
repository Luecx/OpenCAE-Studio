"""Strongly typed public region concepts over the shared resolver."""

from dataclasses import dataclass, field

from ...core import Entity, register_model_type
from opencae.model.selection import RegionDefinition, RegionProjection, RegionScope
from opencae.model.selection.operands import (
    GeometryOperand, MeshElementOperand, MeshFacetOperand, MeshNodeOperand,
    NamedRegionOperand, ReferencePointOperand, UnresolvedOperand, WholeModelOperand,
)


@register_model_type("region")
@dataclass
class Region(Entity):
    scope: RegionScope | str = RegionScope.PART
    definition: RegionDefinition = field(default_factory=RegionDefinition)
    preferred_projection: RegionProjection | str = RegionProjection.NODES
    geometry_backed: bool = True

    def __post_init__(self):
        self.scope = RegionScope(self.scope)
        projection = RegionProjection.coerce(self.preferred_projection)
        allowed = {RegionProjection.NODES, RegionProjection.ELEMENTS, RegionProjection.FACETS}
        if projection not in allowed:
            raise ValueError("A region must be a node, element, or surface region")
        self.preferred_projection = projection
        self.definition = RegionDefinition.from_values(self.definition)
        self._validate_definition()

    def _validate_definition(self) -> None:
        return None

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None


@register_model_type("geometry_region")
@dataclass
class GeometryRegion(Region):
    geometry_backed: bool = field(init=False, default=True)

    def _validate_definition(self) -> None:
        invalid = [type(value).__name__ for value in self.definition.operands if not isinstance(value, (GeometryOperand, UnresolvedOperand))]
        if invalid:
            raise TypeError("GeometryRegion accepts only geometry operands; got " + ", ".join(invalid))


@register_model_type("node_region")
@dataclass
class NodeRegion(Region):
    preferred_projection: RegionProjection = field(init=False, default=RegionProjection.NODES)

    def _validate_definition(self) -> None:
        _reject_operands(self, (GeometryOperand, MeshNodeOperand, MeshElementOperand, ReferencePointOperand, NamedRegionOperand, WholeModelOperand, UnresolvedOperand))


@register_model_type("element_region")
@dataclass
class ElementRegion(Region):
    preferred_projection: RegionProjection = field(init=False, default=RegionProjection.ELEMENTS)

    def _validate_definition(self) -> None:
        _reject_operands(self, (GeometryOperand, MeshElementOperand, NamedRegionOperand, WholeModelOperand, UnresolvedOperand))
        for operand in self.definition.operands:
            if isinstance(operand, GeometryOperand) and operand.dimension == 0:
                raise ValueError("ElementRegion cannot target a geometry vertex")


@register_model_type("surface_region")
@dataclass
class SurfaceRegion(Region):
    preferred_projection: RegionProjection = field(init=False, default=RegionProjection.FACETS)

    def _validate_definition(self) -> None:
        _reject_operands(self, (GeometryOperand, MeshElementOperand, MeshFacetOperand, NamedRegionOperand, WholeModelOperand, UnresolvedOperand))
        for operand in self.definition.operands:
            if isinstance(operand, GeometryOperand) and operand.dimension != 2:
                raise ValueError("SurfaceRegion geometry operands must be faces")


def _reject_operands(region: Region, allowed) -> None:
    invalid = [type(value).__name__ for value in region.definition.operands if not isinstance(value, allowed)]
    if invalid:
        raise TypeError(f"{type(region).__name__} does not accept " + ", ".join(invalid))
