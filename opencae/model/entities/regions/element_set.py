from dataclasses import dataclass

from ...core import register_model_type
from .region import ElementRegion


@register_model_type("element_set")
@dataclass
class ElementSet(ElementRegion):
    """Legacy persisted alias for ElementRegion."""
