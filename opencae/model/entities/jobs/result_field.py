from dataclasses import dataclass

from ...core import Entity, register_model_type


@register_model_type("result_field")
@dataclass
class ResultField(Entity):
    location: str = "Nodal"
    components: int = 1
