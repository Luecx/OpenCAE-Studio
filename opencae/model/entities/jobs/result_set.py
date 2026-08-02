from dataclasses import dataclass, field
from typing import Any

from ...core import Entity, EntityRef, register_model_type
from .result_field import ResultField


@register_model_type("result_set")
@dataclass
class ResultSet(Entity):
    job_ref: EntityRef | None = None
    source_file: str = ""
    status: str = "Unavailable"
    fields: list[ResultField] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None: return None
