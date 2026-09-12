"""Defines spatial field data independently of UI and solver adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ...core import Entity, register_model_type
from .field_interpolation import FieldInterpolation
from .field_location import FieldLocation
from .field_source_kind import FieldSourceKind
from .field_value_kind import FieldValueKind

if TYPE_CHECKING:
    from ..regions import Region


@register_model_type("field_definition")
@dataclass
class FieldDefinition(Entity):
    """Store one typed spatial field definition and its selected value source."""

    location: FieldLocation | str = FieldLocation.NODAL
    components: int = 1
    component_names: list[str] = field(default_factory=lambda: ["Value"])
    region: Region | None = field(
        default=None,
        metadata={"reference_type": "Region"},
    )
    source_type: FieldSourceKind | str = FieldSourceKind.FORMULA
    expression: str = "0.0"
    table: list[list[str]] = field(default_factory=list)
    file_path: str = ""
    interpolation: FieldInterpolation | str = FieldInterpolation.LINEAR
    field_type: FieldValueKind | str = FieldValueKind.SCALAR

    def __setattr__(self, name, value) -> None:
        coercers = {
            "location": FieldLocation.coerce,
            "source_type": FieldSourceKind.coerce,
            "interpolation": FieldInterpolation.coerce,
            "field_type": FieldValueKind.coerce,
        }
        if name in coercers:
            value = coercers[name](value)
        super().__setattr__(name, value)

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
