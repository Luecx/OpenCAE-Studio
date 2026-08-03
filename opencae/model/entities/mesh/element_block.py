from dataclasses import dataclass, field

from ...core import SolverWritable, register_model_type
from ..elements.base import ElementDefinition


@register_model_type("element_block")
@dataclass
class ElementBlock(SolverWritable):
    definition: ElementDefinition
    ids: list[int] = field(default_factory=list)
    connectivity: list[tuple[int, ...]] = field(default_factory=list)

    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None:
        return None
