from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from opencae.model.core.model_registry import register_model_type


class SelectableKind(StrEnum):
    GEOMETRY_VERTEX = "geometry_vertex"
    GEOMETRY_EDGE = "geometry_edge"
    GEOMETRY_FACE = "geometry_face"
    GEOMETRY_CELL = "geometry_cell"
    MESH_NODE = "mesh_node"
    MESH_ELEMENT = "mesh_element"
    MESH_FACET = "mesh_facet"
    REFERENCE_POINT = "reference_point"
    DATUM_POINT = "datum_point"
    DATUM_VECTOR = "datum_vector"
    DATUM_PLANE = "datum_plane"
    NAMED_REGION = "named_region"
    WHOLE_MODEL = "whole_model"

    @classmethod
    def coerce(cls, value) -> "SelectableKind":
        if isinstance(value, cls):
            return value
        text = str(value or "").strip().lower().replace(" ", "_")
        aliases = {
            "vertex": cls.GEOMETRY_VERTEX,
            "point": cls.GEOMETRY_VERTEX,
            "edge": cls.GEOMETRY_EDGE,
            "face": cls.GEOMETRY_FACE,
            "cell": cls.GEOMETRY_CELL,
            "node": cls.MESH_NODE,
            "element": cls.MESH_ELEMENT,
            "facet": cls.MESH_FACET,
            "rp": cls.REFERENCE_POINT,
            "reference_point": cls.REFERENCE_POINT,
            "datum_point": cls.DATUM_POINT,
            "datum_vector": cls.DATUM_VECTOR,
            "datum_plane": cls.DATUM_PLANE,
            "region": cls.NAMED_REGION,
            "set": cls.NAMED_REGION,
            "all": cls.WHOLE_MODEL,
        }
        try:
            return cls(text)
        except ValueError:
            return aliases.get(text, cls.NAMED_REGION)


class RegionProjection(StrEnum):
    NODES = "nodes"
    ELEMENTS = "elements"
    FACETS = "facets"
    SINGLE_CONTROL_NODE = "single_control_node"

    @classmethod
    def coerce(cls, value) -> "RegionProjection | None":
        if value in (None, ""):
            return None
        if isinstance(value, cls):
            return value
        text = str(value).strip().lower().replace(" ", "_")
        aliases = {
            "node_set": cls.NODES,
            "node set": cls.NODES,
            "element_set": cls.ELEMENTS,
            "element set": cls.ELEMENTS,
            "surface": cls.FACETS,
            "control": cls.SINGLE_CONTROL_NODE,
        }
        try:
            return cls(text)
        except ValueError:
            return aliases.get(text)


class RegionScope(StrEnum):
    PART = "Part"
    ASSEMBLY = "Assembly"
    INLINE = "Inline"


class SelectionMultiplicity(StrEnum):
    SINGLE = "single"
    MULTIPLE = "multiple"


class SelectionOperation(StrEnum):
    """How one viewport gesture modifies an existing region selection."""

    REPLACE = "replace"
    ADD = "add"
    REMOVE = "remove"


class NodalLoadDistribution(StrEnum):
    PER_NODE = "per_node"
    TOTAL_UNIFORM = "total_uniform"


@register_model_type("region_requirement")
@dataclass(frozen=True, slots=True)
class RegionRequirement:
    projection: RegionProjection | str = RegionProjection.NODES
    allowed_dimensions: tuple[int, ...] = (0, 1, 2, 3)
    min_count: int = 1
    max_count: int | None = None
    require_unique_occurrence: bool = False

    def __post_init__(self):
        object.__setattr__(self, "projection", RegionProjection(self.projection))
        object.__setattr__(self, "allowed_dimensions", tuple(sorted({int(v) for v in self.allowed_dimensions})))


@dataclass(frozen=True, slots=True)
class SelectionPolicy:
    accepted_kinds: frozenset[SelectableKind]
    multiplicity: SelectionMultiplicity = SelectionMultiplicity.MULTIPLE
    requirement: RegionRequirement = RegionRequirement()

    @classmethod
    def create(cls, kinds, *, multiple=True, requirement=None):
        return cls(
            frozenset(SelectableKind.coerce(value) for value in kinds),
            SelectionMultiplicity.MULTIPLE if multiple else SelectionMultiplicity.SINGLE,
            requirement or RegionRequirement(),
        )
