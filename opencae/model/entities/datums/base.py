from dataclasses import dataclass, field
from typing import Any

from ...core import Entity, register_model_type


@register_model_type("datum")
@dataclass
class Datum(Entity):
    datum_type: str = "Datum"
    method: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    scope: str = "Part"

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
