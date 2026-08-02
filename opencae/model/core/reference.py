from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Generic, TypeVar

from .model_registry import register_model_type

T = TypeVar("T")


@register_model_type("entity_ref")
@dataclass(frozen=True, slots=True)
class EntityRef(Generic[T]):
    entity_id: str = ""
    expected_type: str = ""
    legacy_name: str = ""

    @property
    def is_bound(self) -> bool:
        return bool(self.entity_id)

    def bound_to(self, entity) -> "EntityRef[T]":
        return EntityRef(entity.id, self.expected_type or type(entity).__name__, "")

    @classmethod
    def of(cls, entity, expected_type: str = "") -> "EntityRef":
        if entity is None: return cls(expected_type=expected_type)
        if isinstance(entity, EntityRef): return entity
        if hasattr(entity, "id"): return cls(str(entity.id), expected_type or type(entity).__name__)
        return cls(expected_type=expected_type, legacy_name=str(entity))


class TargetKind(StrEnum):
    UNKNOWN = "Unknown"
    NODE_SET = "Node Set"
    ELEMENT_SET = "Element Set"
    SURFACE = "Surface"
    REFERENCE_POINT = "Reference Point"
    MESH_NODE = "Mesh Node"
    MESH_ELEMENT = "Mesh Element"
    WHOLE_MODEL = "Whole Model"

    @classmethod
    def coerce(cls, value) -> "TargetKind":
        if isinstance(value, cls): return value
        text = str(value or "").strip().casefold()
        aliases = {
            "node set": cls.NODE_SET, "nodeset": cls.NODE_SET,
            "element set": cls.ELEMENT_SET, "elementset": cls.ELEMENT_SET,
            "surface": cls.SURFACE, "reference point": cls.REFERENCE_POINT,
            "referencepoint": cls.REFERENCE_POINT, "rp": cls.REFERENCE_POINT,
            "mesh node": cls.MESH_NODE, "node": cls.MESH_NODE,
            "mesh element": cls.MESH_ELEMENT, "element": cls.MESH_ELEMENT,
            "whole model": cls.WHOLE_MODEL, "all": cls.WHOLE_MODEL,
        }
        return aliases.get(text, cls.UNKNOWN)


@register_model_type("entity_target")
@dataclass(frozen=True, slots=True)
class EntityTarget:
    kind: TargetKind | str = TargetKind.UNKNOWN
    ref: EntityRef = field(default_factory=EntityRef)

    def __post_init__(self): object.__setattr__(self, "kind", TargetKind.coerce(self.kind))
    @property
    def legacy_name(self) -> str: return self.ref.legacy_name


@register_model_type("node_set_target")
@dataclass(frozen=True, slots=True)
class NodeSetTarget(EntityTarget):
    kind: TargetKind = field(init=False, default=TargetKind.NODE_SET)


@register_model_type("element_set_target")
@dataclass(frozen=True, slots=True)
class ElementSetTarget(EntityTarget):
    kind: TargetKind = field(init=False, default=TargetKind.ELEMENT_SET)


@register_model_type("surface_target")
@dataclass(frozen=True, slots=True)
class SurfaceTarget(EntityTarget):
    kind: TargetKind = field(init=False, default=TargetKind.SURFACE)


@register_model_type("reference_point_target")
@dataclass(frozen=True, slots=True)
class ReferencePointTarget(EntityTarget):
    kind: TargetKind = field(init=False, default=TargetKind.REFERENCE_POINT)


@register_model_type("whole_model_target")
@dataclass(frozen=True, slots=True)
class WholeModelTarget(EntityTarget):
    kind: TargetKind = field(init=False, default=TargetKind.WHOLE_MODEL)


@register_model_type("mesh_node_target")
@dataclass(frozen=True, slots=True)
class MeshNodeTarget:
    owner_ref: EntityRef = field(default_factory=EntityRef)
    node_id: int = 0
    kind: TargetKind = field(init=False, default=TargetKind.MESH_NODE)


@register_model_type("mesh_element_target")
@dataclass(frozen=True, slots=True)
class MeshElementTarget:
    owner_ref: EntityRef = field(default_factory=EntityRef)
    element_id: int = 0
    kind: TargetKind = field(init=False, default=TargetKind.MESH_ELEMENT)


TargetRef = EntityTarget | MeshNodeTarget | MeshElementTarget


def entity_target(ref, kind: TargetKind | str = TargetKind.UNKNOWN) -> EntityTarget:
    resolved = TargetKind.coerce(kind)
    cls = {
        TargetKind.NODE_SET: NodeSetTarget,
        TargetKind.ELEMENT_SET: ElementSetTarget,
        TargetKind.SURFACE: SurfaceTarget,
        TargetKind.REFERENCE_POINT: ReferencePointTarget,
        TargetKind.WHOLE_MODEL: WholeModelTarget,
    }.get(resolved)
    reference = as_entity_ref(ref, resolved.value.replace(" ", ""))
    return cls(ref=reference) if cls else EntityTarget(resolved, reference)


def as_entity_ref(value, expected_type: str = "") -> EntityRef:
    if value is None: return EntityRef(expected_type=expected_type)
    if isinstance(value, EntityRef):
        if expected_type and not value.expected_type:
            return EntityRef(value.entity_id, expected_type, value.legacy_name)
        return value
    return EntityRef.of(value, expected_type)


def as_target(value, kind: TargetKind | str = TargetKind.UNKNOWN) -> TargetRef | None:
    if value is None or value == "": return None
    if isinstance(value, (EntityTarget, MeshNodeTarget, MeshElementTarget)): return value
    return entity_target(value, kind)


def target_for_entity(entity) -> EntityTarget:
    from opencae.model.entities.regions import ElementSet, NodeSet, ReferencePoint, Surface
    kind = TargetKind.UNKNOWN
    if isinstance(entity, ReferencePoint): kind = TargetKind.REFERENCE_POINT
    elif isinstance(entity, Surface) or getattr(entity, "region_type", "") == "Surface": kind = TargetKind.SURFACE
    elif isinstance(entity, ElementSet) or getattr(entity, "region_type", "") == "Element Set": kind = TargetKind.ELEMENT_SET
    elif isinstance(entity, NodeSet) or getattr(entity, "region_type", "") == "Node Set": kind = TargetKind.NODE_SET
    return entity_target(EntityRef.of(entity, type(entity).__name__), kind)
