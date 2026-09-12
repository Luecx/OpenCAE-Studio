"""Typed optional associations between finite-element entities and CAD topology."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, MutableMapping
from dataclasses import dataclass, field
from typing import Any

from ...core import register_model_type
from .geometry_entity_ref import GeometryEntityRef


@register_model_type("geometry_association_entry")
@dataclass
class GeometryAssociationEntry:
    """Persist one typed CAD key and its associated FE values."""

    geometry: GeometryEntityRef = field(
        default_factory=lambda: GeometryEntityRef(0, 1)
    )
    values: list[Any] = field(
        default_factory=list,
        metadata={"project_index": False},
    )


@register_model_type("geometry_association_map")
@dataclass
class GeometryAssociationMap(MutableMapping[str, list[Any]]):
    """Mapping with typed persisted keys and legacy string lookup support."""

    value_kind: str = "ids"
    entries: list[GeometryAssociationEntry] = field(
        default_factory=list,
        metadata={"project_index": False},
    )

    def __post_init__(self) -> None:
        self.value_kind = str(self.value_kind or "ids")
        normalized: list[GeometryAssociationEntry] = []
        seen: set[GeometryEntityRef] = set()
        for raw in self.entries:
            entry = (
                raw
                if isinstance(raw, GeometryAssociationEntry)
                else GeometryAssociationEntry(**raw)
            )
            ref = GeometryEntityRef.parse(entry.geometry)
            if ref in seen:
                raise ValueError(f"Duplicate geometry association for {ref}")
            seen.add(ref)
            normalized.append(
                GeometryAssociationEntry(
                    ref,
                    self._normalize_values(entry.values),
                )
            )
        self.entries = normalized

    @classmethod
    def from_mapping(
        cls,
        values=None,
        *,
        value_kind="ids",
    ) -> "GeometryAssociationMap":
        if isinstance(values, cls):
            if values.value_kind == value_kind:
                return values
            values = dict(values)
        result = cls(value_kind=value_kind)
        for key, members in dict(values or {}).items():
            result[key] = members
        return result

    def __getitem__(self, key) -> list[Any]:
        ref = GeometryEntityRef.parse(key)
        for entry in self.entries:
            if entry.geometry == ref:
                return entry.values
        raise KeyError(str(ref))

    def __setitem__(self, key, value) -> None:
        ref = GeometryEntityRef.parse(key)
        normalized = self._normalize_values(value)
        for entry in self.entries:
            if entry.geometry == ref:
                entry.values = normalized
                return
        self.entries.append(GeometryAssociationEntry(ref, normalized))

    def __delitem__(self, key) -> None:
        ref = GeometryEntityRef.parse(key)
        for index, entry in enumerate(self.entries):
            if entry.geometry == ref:
                del self.entries[index]
                return
        raise KeyError(str(ref))

    def __iter__(self) -> Iterator[str]:
        return (str(entry.geometry) for entry in self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def __eq__(self, other) -> bool:
        """Preserve normal mapping equality for the legacy public mapping facade."""
        if isinstance(other, Mapping):
            return dict(self.items()) == dict(other.items())
        return NotImplemented

    def get_typed(self, key, default=None):
        try:
            return self[key]
        except (KeyError, TypeError, ValueError):
            return default

    def typed_items(self):
        return tuple((entry.geometry, entry.values) for entry in self.entries)

    def discard_ids(self, ids) -> bool:
        """Remove node/element IDs from all memberships and empty entries."""
        unwanted = {int(value) for value in ids}
        if not unwanted:
            return False
        changed = False
        kept: list[GeometryAssociationEntry] = []
        for entry in self.entries:
            if self.value_kind == "facets":
                values = [
                    value
                    for value in entry.values
                    if int(value[0]) not in unwanted
                ]
            else:
                values = [
                    value
                    for value in entry.values
                    if int(value) not in unwanted
                ]
            changed |= len(values) != len(entry.values)
            if values:
                kept.append(GeometryAssociationEntry(entry.geometry, values))
        if changed:
            self.entries = kept
        return changed

    def _normalize_values(self, values) -> list[Any]:
        if self.value_kind == "facets":
            result = []
            for value in values or ():
                if len(value) != 2:
                    raise ValueError(
                        "Facet associations require (element_id, local_face)"
                    )
                result.append((int(value[0]), str(value[1])))
            return result
        return [int(value) for value in (values or ())]


@register_model_type("mesh_association_store")
@dataclass
class MeshAssociationStore:
    """Own optional CAD-to-mesh associations separately from FE storage."""

    nodes: GeometryAssociationMap = field(
        default_factory=lambda: GeometryAssociationMap(value_kind="ids"),
        metadata={"project_index": False},
    )
    elements: GeometryAssociationMap = field(
        default_factory=lambda: GeometryAssociationMap(value_kind="ids"),
        metadata={"project_index": False},
    )
    facets: GeometryAssociationMap = field(
        default_factory=lambda: GeometryAssociationMap(value_kind="facets"),
        metadata={"project_index": False},
    )

    def __post_init__(self) -> None:
        self.nodes = GeometryAssociationMap.from_mapping(
            self.nodes,
            value_kind="ids",
        )
        self.elements = GeometryAssociationMap.from_mapping(
            self.elements,
            value_kind="ids",
        )
        self.facets = GeometryAssociationMap.from_mapping(
            self.facets,
            value_kind="facets",
        )

    @classmethod
    def from_legacy(
        cls,
        nodes=None,
        elements=None,
        facets=None,
    ) -> "MeshAssociationStore":
        return cls(
            GeometryAssociationMap.from_mapping(nodes, value_kind="ids"),
            GeometryAssociationMap.from_mapping(elements, value_kind="ids"),
            GeometryAssociationMap.from_mapping(facets, value_kind="facets"),
        )

    @property
    def empty(self) -> bool:
        return not (self.nodes or self.elements or self.facets)

    def detach(self, *, node_ids=(), element_ids=()) -> bool:
        changed = self.nodes.discard_ids(node_ids)
        changed |= self.elements.discard_ids(element_ids)
        changed |= self.facets.discard_ids(element_ids)
        return changed
