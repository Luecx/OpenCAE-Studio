from dataclasses import dataclass, field
from ...core import register_model_type
from opencae.model.selection import NodalLoadDistribution
from .base import Load


@register_model_type("concentrated_load")
@dataclass
class ConcentratedLoad(Load):
    load_type: str = field(init=False, default="Concentrated Load")
    components: list[float] = field(default_factory=lambda: [0.0] * 6)
    distribution: NodalLoadDistribution | str = NodalLoadDistribution.PER_NODE

    def __post_init__(self):
        super().__post_init__()
        self.distribution = NodalLoadDistribution(self.distribution)
