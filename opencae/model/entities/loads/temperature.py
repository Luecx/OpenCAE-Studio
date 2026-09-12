"""Defines temperature loads with direct Field relationships."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ...core import register_model_type
from .base import Load

if TYPE_CHECKING:
    from ..fields import FieldDefinition


@register_model_type("temperature_load")
@dataclass
class TemperatureLoad(Load):
    load_type: str = field(init=False, default="Temperature")
    temperature_field: FieldDefinition | None = field(
        default=None,
        metadata={"reference_type": "FieldDefinition"},
    )
    reference_temperature: float = 0.0
