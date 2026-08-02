from dataclasses import dataclass, field

from ...core import register_model_type
from .base import Datum


@register_model_type("datum_plane")
@dataclass
class DatumPlane(Datum):
    datum_type: str = field(init=False, default="Plane")
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
    normal: tuple[float, float, float] = (0.0, 0.0, 1.0)
    axis: tuple[float, float, float] = (1.0, 0.0, 0.0)
