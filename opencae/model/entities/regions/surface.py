from dataclasses import dataclass

from ...core import register_model_type
from .region import SurfaceRegion


@register_model_type("surface")
@dataclass
class Surface(SurfaceRegion):
    """Legacy persisted alias for SurfaceRegion."""
