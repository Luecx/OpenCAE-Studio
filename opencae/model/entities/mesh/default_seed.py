from dataclasses import dataclass, field

from ...core import register_model_type
from .seed import Seed


@register_model_type("default_seed")
@dataclass
class DefaultSeed(Seed):
    seed_type: str = field(init=False, default="Default")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
