from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .model_registry import register_model_type
from .reference import EntityRef, as_entity_ref

_LABEL = re.compile(r"^(?P<kind>Vertex|Edge|Face|Cell|Node|Element)-(?P<tag>\d+)$", re.I)


class RegionMemberKind(StrEnum):
    UNKNOWN = "Unknown"
    VERTEX = "Vertex"
    EDGE = "Edge"
    FACE = "Face"
    CELL = "Cell"
    NODE = "Node"
    ELEMENT = "Element"
    REFERENCE_POINT = "Reference Point"

    @classmethod
    def coerce(cls, value: Any) -> "RegionMemberKind":
        if isinstance(value, cls):
            return value
        text = str(value or "").strip().replace("_", " ").casefold()
        aliases = {
            "vertex": cls.VERTEX,
            "point": cls.VERTEX,
            "edge": cls.EDGE,
            "face": cls.FACE,
            "cell": cls.CELL,
            "node": cls.NODE,
            "element": cls.ELEMENT,
            "reference point": cls.REFERENCE_POINT,
            "referencepoint": cls.REFERENCE_POINT,
            "rp": cls.REFERENCE_POINT,
        }
        return aliases.get(text, cls.UNKNOWN)


@register_model_type("region_member_ref")
@dataclass(frozen=True, slots=True)
class RegionMemberRef:
    """Stable reference to a CAD/mesh member or a Reference Point.

    ``owner_ref`` identifies the Part or Assembly Instance whose local topology
    owns ``tag``. Reference Points additionally use ``entity_ref`` because their
    identity is an Entity ID rather than a topology number.
    """

    kind: RegionMemberKind | str = RegionMemberKind.UNKNOWN
    owner_ref: EntityRef = field(default_factory=EntityRef)
    tag: int | str = 0
    entity_ref: EntityRef | None = None
    legacy_label: str = ""

    def __post_init__(self) -> None:
        kind = RegionMemberKind.coerce(self.kind)
        object.__setattr__(self, "kind", kind)
        if kind in {
            RegionMemberKind.VERTEX,
            RegionMemberKind.EDGE,
            RegionMemberKind.FACE,
            RegionMemberKind.CELL,
            RegionMemberKind.NODE,
            RegionMemberKind.ELEMENT,
        }:
            try:
                object.__setattr__(self, "tag", int(self.tag))
            except (TypeError, ValueError):
                object.__setattr__(self, "kind", RegionMemberKind.UNKNOWN)

    @property
    def is_bound(self) -> bool:
        if self.kind == RegionMemberKind.REFERENCE_POINT:
            return bool(self.entity_ref and self.entity_ref.entity_id)
        return self.kind != RegionMemberKind.UNKNOWN and bool(self.owner_ref.entity_id)

    def __str__(self) -> str:
        if self.legacy_label:
            return self.legacy_label
        if self.kind == RegionMemberKind.REFERENCE_POINT:
            return self.entity_ref.legacy_name if self.entity_ref else "Reference Point"
        if self.kind == RegionMemberKind.UNKNOWN:
            return "Unknown"
        return f"{self.kind.value}-{self.tag}"


def member_from_selection(project, entity: dict[str, Any], default_owner=None) -> RegionMemberRef | None:
    """Convert one viewport selection record into a persistent member ref."""
    kind_text = str(entity.get("kind") or entity.get("mesh_entity") or "").strip().lower()
    if kind_text in {"datum", "datum_point", "datum_vector", "datum_plane"}:
        return None

    owner = _selection_owner(project, entity, default_owner)
    if kind_text == "rp":
        point = project.try_resolve(str(entity.get("tag") or ""))
        if point is None:
            return None
        return RegionMemberRef(
            RegionMemberKind.REFERENCE_POINT,
            EntityRef.of(owner, type(owner).__name__) if owner is not None else EntityRef(),
            0,
            EntityRef.of(point, "ReferencePoint"),
        )

    kind = RegionMemberKind.coerce(kind_text)
    if kind == RegionMemberKind.UNKNOWN or owner is None:
        return None
    try:
        tag = int(entity.get("tag"))
    except (TypeError, ValueError):
        return None
    return RegionMemberRef(kind, EntityRef.of(owner, type(owner).__name__), tag)


def local_member_ref(owner, value) -> RegionMemberRef:
    """Create a typed Part-local topology reference from a UI label."""
    if isinstance(value, RegionMemberRef):
        if value.owner_ref.entity_id:
            return value
        return RegionMemberRef(value.kind, EntityRef.of(owner, type(owner).__name__), value.tag, value.entity_ref, value.legacy_label)
    text = str(value or "").strip().replace("/", ".")
    local = text.split(".")[-1]
    match = _LABEL.match(local)
    if match:
        return RegionMemberRef(
            RegionMemberKind.coerce(match.group("kind")),
            EntityRef.of(owner, type(owner).__name__),
            int(match.group("tag")),
        )
    return RegionMemberRef(
        RegionMemberKind.UNKNOWN,
        EntityRef.of(owner, type(owner).__name__),
        legacy_label=text,
    )


def local_member_refs(owner, values) -> list[RegionMemberRef]:
    result = []
    for value in values or ():
        member = local_member_ref(owner, value)
        if member not in result:
            result.append(member)
    return result


def members_from_selection(project, selection, default_owner=None) -> list[RegionMemberRef]:
    items = selection.get("entities", [selection]) if isinstance(selection, dict) else []
    result: list[RegionMemberRef] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        member = member_from_selection(project, item, default_owner)
        if member is not None and member not in result:
            result.append(member)
    return result


def bind_region_member(project, index, member, parent) -> tuple[RegionMemberRef, str | None]:
    """Bind a typed or legacy region member using the current project graph."""
    if isinstance(member, RegionMemberRef):
        return _bind_typed_member(project, index, member, parent)
    return _parse_legacy_member(project, index, str(member or ""), parent)


def region_member_label(project, member, *, qualify_part: bool = False) -> str:
    """Return the current UI/export label without persisting mutable names."""
    if not isinstance(member, RegionMemberRef):
        return str(member)
    owner = project.try_resolve(member.owner_ref) if member.owner_ref.entity_id else None
    if member.kind == RegionMemberKind.REFERENCE_POINT:
        point = project.try_resolve(member.entity_ref) if member.entity_ref else None
        label = point.name if point is not None else member.legacy_label or "Reference Point"
    elif member.kind == RegionMemberKind.UNKNOWN:
        return member.legacy_label or "Unknown"
    else:
        label = f"{member.kind.value}-{member.tag}"
    if owner is None:
        return label
    from opencae.model.entities.assembly import Instance
    from opencae.model.entities.parts import Part
    if isinstance(owner, Instance) or (qualify_part and isinstance(owner, Part)):
        return f"{owner.name}.{label}"
    return label


def region_member_local_label(project, member) -> str:
    """Return the local label understood by one Part mesh."""
    if not isinstance(member, RegionMemberRef):
        return str(member)
    if member.kind == RegionMemberKind.REFERENCE_POINT:
        point = project.try_resolve(member.entity_ref) if member.entity_ref else None
        return point.name if point is not None else member.legacy_label
    if member.kind == RegionMemberKind.UNKNOWN:
        return member.legacy_label
    return f"{member.kind.value}-{member.tag}"


def member_owner_id(member) -> str:
    return member.owner_ref.entity_id if isinstance(member, RegionMemberRef) else ""


def _selection_owner(project, entity, default_owner):
    instance_id = str(entity.get("instance_id") or "")
    if instance_id:
        owner = project.try_resolve(instance_id)
        if owner is not None:
            return owner
    instance_name = str(entity.get("instance") or "").strip()
    if instance_name:
        matches = [item for item in project.assembly.instances if item.name.casefold() == instance_name.casefold()]
        if len(matches) == 1:
            return matches[0]
    return default_owner


def _bind_typed_member(project, index, member: RegionMemberRef, parent):
    owner_ref = member.owner_ref
    entity_ref = member.entity_ref
    errors: list[str] = []

    if owner_ref and not owner_ref.entity_id and owner_ref.legacy_name:
        owner = _find_owner(project, index, owner_ref.legacy_name, parent)
        if owner is None:
            errors.append(f"owner '{owner_ref.legacy_name}' was not found")
        else:
            owner_ref = EntityRef.of(owner, type(owner).__name__)
    elif owner_ref and owner_ref.entity_id and index.try_resolve(owner_ref) is None:
        errors.append(f"owner '{owner_ref.entity_id}' does not exist")

    if member.kind == RegionMemberKind.REFERENCE_POINT:
        if entity_ref is None:
            errors.append("Reference Point entity is missing")
        elif not entity_ref.entity_id and entity_ref.legacy_name:
            point = _find_reference_point(project, index, entity_ref.legacy_name, owner_ref, parent)
            if point is None:
                errors.append(f"Reference Point '{entity_ref.legacy_name}' was not found")
            else:
                entity_ref = EntityRef.of(point, "ReferencePoint")
        elif entity_ref.entity_id and index.try_resolve(entity_ref) is None:
            errors.append(f"Reference Point '{entity_ref.entity_id}' does not exist")

    bound = RegionMemberRef(member.kind, owner_ref, member.tag, entity_ref, "" if not errors else member.legacy_label)
    return bound, "; ".join(errors) if errors else None


def _parse_legacy_member(project, index, text: str, parent):
    text = text.strip().replace("/", ".")
    if not text:
        return RegionMemberRef(legacy_label=text), "empty member"

    owner, local = _split_owner(project, text, parent)
    match = _LABEL.match(local)
    if match:
        kind = RegionMemberKind.coerce(match.group("kind"))
        if owner is None:
            return RegionMemberRef(kind, legacy_label=text, tag=int(match.group("tag"))), f"owner for '{text}' was not found"
        return RegionMemberRef(kind, EntityRef.of(owner, type(owner).__name__), int(match.group("tag"))), None

    point = _find_reference_point(project, index, local, EntityRef.of(owner) if owner else EntityRef(), parent)
    if point is not None:
        return RegionMemberRef(
            RegionMemberKind.REFERENCE_POINT,
            EntityRef.of(owner, type(owner).__name__) if owner is not None else EntityRef(),
            0,
            EntityRef.of(point, "ReferencePoint"),
        ), None

    return RegionMemberRef(RegionMemberKind.UNKNOWN, EntityRef.of(owner) if owner else EntityRef(), 0, None, text), f"'{text}' was not found"


def _split_owner(project, text, parent):
    from opencae.model.entities.assembly import Assembly
    from opencae.model.entities.parts import Part

    if isinstance(parent, Part):
        return parent, text
    if isinstance(parent, Assembly):
        instances = sorted(project.assembly.instances, key=lambda item: len(item.name), reverse=True)
        folded = text.casefold()
        for instance in instances:
            prefix = f"{instance.name}."
            if folded.startswith(prefix.casefold()):
                return instance, text[len(prefix):]
        parts = sorted(project.parts, key=lambda item: len(item.name), reverse=True)
        for part in parts:
            prefix = f"{part.name}."
            if folded.startswith(prefix.casefold()):
                return part, text[len(prefix):]
        return None, text
    return parent, text


def _find_owner(project, index, name: str, parent):
    from opencae.model.entities.assembly import Assembly
    from opencae.model.entities.parts import Part
    if isinstance(parent, Part):
        return parent if parent.name.casefold() == name.casefold() else None
    if isinstance(parent, Assembly):
        matches = [item for item in project.assembly.instances if item.name.casefold() == name.casefold()]
        return matches[0] if len(matches) == 1 else None
    matches = [item for item in (*project.parts, *project.assembly.instances) if item.name.casefold() == name.casefold()]
    return matches[0] if len(matches) == 1 else None


def _find_reference_point(project, index, name: str, owner_ref: EntityRef, parent):
    from opencae.model.entities.assembly import Assembly, Instance
    from opencae.model.entities.parts import Part

    text = name.removeprefix("RP-").casefold()
    owner = index.try_resolve(owner_ref) if owner_ref and owner_ref.entity_id else None
    if isinstance(owner, Instance):
        part = index.try_resolve(owner.part_ref)
        candidates = tuple(getattr(part, "reference_points", ())) if part else ()
    elif isinstance(owner, Part):
        candidates = tuple(owner.reference_points)
    elif isinstance(parent, Part):
        candidates = tuple(parent.reference_points)
    elif isinstance(parent, Assembly):
        candidates = tuple(project.assembly.reference_points)
    else:
        candidates = tuple(project.assembly.reference_points)
    matches = [item for item in candidates if item.name.casefold() == text or f"rp-{item.name}".casefold() == name.casefold()]
    return matches[0] if len(matches) == 1 else None
