"""Persistent selection operands built from domain objects rather than IDs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from opencae.model.core.model_registry import register_model_type
from .types import SelectableKind

if TYPE_CHECKING:
    from opencae.model.core.entity import Entity
    from opencae.model.entities.assembly import Instance
    from opencae.model.entities.fem import Element, Node
    from opencae.model.entities.regions import ReferencePoint, Region


@register_model_type("geometry_operand")
@dataclass(frozen=True, slots=True)
class GeometryOperand:
    owner: Entity | None = field(
        default=None,
        metadata={"reference_type": "Entity"},
    )
    dimension: int = 0
    tag: int = 0
    instance: Instance | None = field(
        default=None,
        metadata={"reference_type": "Instance"},
    )
    topology_revision: str = ""
    kind: SelectableKind = field(init=False, default=SelectableKind.GEOMETRY_VERTEX)

    def __post_init__(self):
        object.__setattr__(self, "dimension", int(self.dimension))
        object.__setattr__(self, "tag", int(self.tag))
        kind = {
            0: SelectableKind.GEOMETRY_VERTEX,
            1: SelectableKind.GEOMETRY_EDGE,
            2: SelectableKind.GEOMETRY_FACE,
            3: SelectableKind.GEOMETRY_CELL,
        }.get(int(self.dimension), SelectableKind.GEOMETRY_VERTEX)
        object.__setattr__(self, "kind", kind)


@register_model_type("mesh_node_operand")
@dataclass(frozen=True, slots=True)
class MeshNodeOperand:
    owner: Entity | None = field(
        default=None,
        metadata={"reference_type": "Entity"},
    )
    node: Node | None = field(
        default=None,
        metadata={"mesh_reference": "node"},
    )
    instance: Instance | None = field(
        default=None,
        metadata={"reference_type": "Instance"},
    )
    mesh_revision: str = ""
    kind: SelectableKind = field(init=False, default=SelectableKind.MESH_NODE)


@register_model_type("mesh_element_operand")
@dataclass(frozen=True, slots=True)
class MeshElementOperand:
    owner: Entity | None = field(
        default=None,
        metadata={"reference_type": "Entity"},
    )
    element: Element | None = field(
        default=None,
        metadata={"mesh_reference": "element"},
    )
    instance: Instance | None = field(
        default=None,
        metadata={"reference_type": "Instance"},
    )
    mesh_revision: str = ""
    kind: SelectableKind = field(init=False, default=SelectableKind.MESH_ELEMENT)


@register_model_type("mesh_facet_operand")
@dataclass(frozen=True, slots=True)
class MeshFacetOperand:
    owner: Entity | None = field(
        default=None,
        metadata={"reference_type": "Entity"},
    )
    element: Element | None = field(
        default=None,
        metadata={"mesh_reference": "element"},
    )
    local_face: str = ""
    instance: Instance | None = field(
        default=None,
        metadata={"reference_type": "Instance"},
    )
    mesh_revision: str = ""
    kind: SelectableKind = field(init=False, default=SelectableKind.MESH_FACET)


@register_model_type("reference_point_operand")
@dataclass(frozen=True, slots=True)
class ReferencePointOperand:
    reference_point: ReferencePoint | None = field(
        default=None,
        metadata={"reference_type": "ReferencePoint"},
    )
    instance: Instance | None = field(
        default=None,
        metadata={"reference_type": "Instance"},
    )
    kind: SelectableKind = field(init=False, default=SelectableKind.REFERENCE_POINT)


@register_model_type("named_region_operand")
@dataclass(frozen=True, slots=True)
class NamedRegionOperand:
    region: Region | None = field(
        default=None,
        metadata={"reference_type": "Region"},
    )
    instance: Instance | None = field(
        default=None,
        metadata={"reference_type": "Instance"},
    )
    kind: SelectableKind = field(init=False, default=SelectableKind.NAMED_REGION)


@register_model_type("whole_model_operand")
@dataclass(frozen=True, slots=True)
class WholeModelOperand:
    owner: Entity | None = field(
        default=None,
        metadata={"reference_type": "Entity"},
    )
    instance: Instance | None = field(
        default=None,
        metadata={"reference_type": "Instance"},
    )
    kind: SelectableKind = field(init=False, default=SelectableKind.WHOLE_MODEL)


@register_model_type("unresolved_operand")
@dataclass(frozen=True, slots=True)
class UnresolvedOperand:
    legacy_label: str = ""
    expected_kind: str = ""
    kind: SelectableKind = field(init=False, default=SelectableKind.NAMED_REGION)


RegionOperand = (
    GeometryOperand | MeshNodeOperand | MeshElementOperand | MeshFacetOperand |
    ReferencePointOperand | NamedRegionOperand | WholeModelOperand | UnresolvedOperand
)


def operand_key(value: RegionOperand) -> tuple:
    if isinstance(value, GeometryOperand):
        return (
            value.kind, _id(value.instance), _id(value.owner), value.dimension,
            value.tag, value.topology_revision,
        )
    if isinstance(value, MeshNodeOperand):
        return (
            value.kind, _id(value.instance), _id(value.owner),
            getattr(value.node, "id", 0), value.mesh_revision,
        )
    if isinstance(value, MeshElementOperand):
        return (
            value.kind, _id(value.instance), _id(value.owner),
            getattr(value.element, "id", 0), value.mesh_revision,
        )
    if isinstance(value, MeshFacetOperand):
        return (
            value.kind, _id(value.instance), _id(value.owner),
            getattr(value.element, "id", 0), value.local_face, value.mesh_revision,
        )
    if isinstance(value, ReferencePointOperand):
        return (value.kind, _id(value.instance), _id(value.reference_point))
    if isinstance(value, NamedRegionOperand):
        return (value.kind, _id(value.instance), _id(value.region))
    if isinstance(value, UnresolvedOperand):
        return ("unresolved", value.legacy_label, value.expected_kind)
    return (value.kind, _id(value.instance), _id(value.owner))


def _id(value) -> str:
    return str(getattr(value, "id", getattr(value, "entity_id", "")) or "")
