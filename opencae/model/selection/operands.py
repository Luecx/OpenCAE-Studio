from __future__ import annotations

from dataclasses import dataclass, field

from opencae.model.core.model_registry import register_model_type
from opencae.model.core.reference import EntityRef
from .types import SelectableKind


@register_model_type("geometry_operand")
@dataclass(frozen=True, slots=True)
class GeometryOperand:
    owner_ref: EntityRef = field(default_factory=EntityRef)
    dimension: int = 0
    tag: int = 0
    instance_ref: EntityRef | None = None
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
    owner_ref: EntityRef = field(default_factory=EntityRef)
    node_id: int = 0
    instance_ref: EntityRef | None = None
    mesh_revision: str = ""
    kind: SelectableKind = field(init=False, default=SelectableKind.MESH_NODE)

    def __post_init__(self): object.__setattr__(self, "node_id", int(self.node_id))


@register_model_type("mesh_element_operand")
@dataclass(frozen=True, slots=True)
class MeshElementOperand:
    owner_ref: EntityRef = field(default_factory=EntityRef)
    element_id: int = 0
    instance_ref: EntityRef | None = None
    mesh_revision: str = ""
    kind: SelectableKind = field(init=False, default=SelectableKind.MESH_ELEMENT)

    def __post_init__(self): object.__setattr__(self, "element_id", int(self.element_id))


@register_model_type("mesh_facet_operand")
@dataclass(frozen=True, slots=True)
class MeshFacetOperand:
    owner_ref: EntityRef = field(default_factory=EntityRef)
    element_id: int = 0
    local_face: str = ""
    instance_ref: EntityRef | None = None
    mesh_revision: str = ""
    kind: SelectableKind = field(init=False, default=SelectableKind.MESH_FACET)

    def __post_init__(self): object.__setattr__(self, "element_id", int(self.element_id))


@register_model_type("reference_point_operand")
@dataclass(frozen=True, slots=True)
class ReferencePointOperand:
    reference_point_ref: EntityRef = field(default_factory=lambda: EntityRef(expected_type="ReferencePoint"))
    instance_ref: EntityRef | None = None
    kind: SelectableKind = field(init=False, default=SelectableKind.REFERENCE_POINT)


@register_model_type("named_region_operand")
@dataclass(frozen=True, slots=True)
class NamedRegionOperand:
    region_ref: EntityRef = field(default_factory=lambda: EntityRef(expected_type="Region"))
    instance_ref: EntityRef | None = None
    kind: SelectableKind = field(init=False, default=SelectableKind.NAMED_REGION)


@register_model_type("whole_model_operand")
@dataclass(frozen=True, slots=True)
class WholeModelOperand:
    owner_ref: EntityRef | None = None
    instance_ref: EntityRef | None = None
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
        return (value.kind, _id(value.instance_ref), value.owner_ref.entity_id, value.dimension, value.tag, value.topology_revision)
    if isinstance(value, MeshNodeOperand):
        return (value.kind, _id(value.instance_ref), value.owner_ref.entity_id, value.node_id, value.mesh_revision)
    if isinstance(value, MeshElementOperand):
        return (value.kind, _id(value.instance_ref), value.owner_ref.entity_id, value.element_id, value.mesh_revision)
    if isinstance(value, MeshFacetOperand):
        return (value.kind, _id(value.instance_ref), value.owner_ref.entity_id, value.element_id, value.local_face, value.mesh_revision)
    if isinstance(value, ReferencePointOperand):
        return (value.kind, _id(value.instance_ref), value.reference_point_ref.entity_id)
    if isinstance(value, NamedRegionOperand):
        return (value.kind, _id(value.instance_ref), value.region_ref.entity_id)
    if isinstance(value, UnresolvedOperand): return ("unresolved", value.legacy_label, value.expected_kind)
    return (value.kind, _id(value.instance_ref), _id(value.owner_ref))


def _id(ref) -> str:
    return ref.entity_id if ref else ""
