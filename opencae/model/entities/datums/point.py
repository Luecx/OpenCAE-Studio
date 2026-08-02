from dataclasses import dataclass, field

from ...core import register_model_type
from .base import Datum


@register_model_type("datum_point")
@dataclass
class DatumPoint(Datum):
    datum_type: str = field(init=False, default="Point")
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
