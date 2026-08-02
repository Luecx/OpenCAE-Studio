from dataclasses import dataclass, field

from ...core import register_model_type
from .base import Datum


@register_model_type("datum_vector")
@dataclass
class DatumVector(Datum):
    datum_type: str = field(init=False, default="Vector")
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
    direction: tuple[float, float, float] = (1.0, 0.0, 0.0)
