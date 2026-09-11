"""Typed references to CAD topology entities used by mesh associations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import re

from ...core import register_model_type


class GeometryDimension(IntEnum):
    """Topological dimension of one geometry entity."""

    VERTEX = 0
    EDGE = 1
    FACE = 2
    CELL = 3

    @classmethod
    def coerce(cls, value) -> "GeometryDimension":
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            text = value.strip().upper()
            aliases = {
                "POINT": cls.VERTEX,
                "VERTEX": cls.VERTEX,
                "EDGE": cls.EDGE,
                "FACE": cls.FACE,
                "SURFACE": cls.FACE,
                "CELL": cls.CELL,
                "VOLUME": cls.CELL,
            }
            if text in aliases:
                return aliases[text]
        return cls(int(value))

    @property
    def label(self) -> str:
        return {
            self.VERTEX: "Vertex",
            self.EDGE: "Edge",
            self.FACE: "Face",
            self.CELL: "Cell",
        }[self]


_GEOMETRY_REF = re.compile(
    r"^\s*(vertex|point|edge|face|surface|cell|volume)\s*[-:#]?\s*(\d+)\s*$",
    re.I,
)


@register_model_type("geometry_entity_ref")
@dataclass(frozen=True, slots=True)
class GeometryEntityRef:
    """Stable typed identity of one CAD topology entity within a Part."""

    dimension: GeometryDimension | int | str = GeometryDimension.VERTEX
    tag: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "dimension", GeometryDimension.coerce(self.dimension))
        tag = int(self.tag)
        if tag <= 0:
            raise ValueError("Geometry entity tags must be positive")
        object.__setattr__(self, "tag", tag)

    def __str__(self) -> str:
        return f"{self.dimension.label}-{self.tag}"

    @classmethod
    def parse(cls, value) -> "GeometryEntityRef":
        if isinstance(value, cls):
            return value
        if isinstance(value, tuple) and len(value) == 2:
            return cls(value[0], value[1])
        if isinstance(value, str):
            match = _GEOMETRY_REF.match(value)
            if not match:
                raise ValueError(f"Invalid geometry entity reference: {value!r}")
            return cls(match.group(1), int(match.group(2)))
        raise TypeError(
            f"Cannot convert {type(value).__name__} to GeometryEntityRef"
        )
