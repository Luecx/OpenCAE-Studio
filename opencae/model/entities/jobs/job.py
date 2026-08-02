from dataclasses import dataclass, field
from typing import Any

from ...core import Entity, register_model_type


@register_model_type("job")
@dataclass
class Job(Entity):
    analysis_name: str = ""
    solver: str = "FEMaster"
    status: str = "Not started"
    input_deck: str = ""
    settings: dict[str, Any] = field(default_factory=dict)

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
