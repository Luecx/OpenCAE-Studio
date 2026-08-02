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
        from opencae.solvers.femaster_dsl.command import command
        from opencae.solvers.femaster_dsl.element_types import element_type
        type_name = element_type(self.definition, len(self.connectivity[0]) if self.connectivity else None)
        if type_name: command(writer, "ELEMENT", [(eid, *nodes) for eid, nodes in zip(self.ids, self.connectivity)], TYPE=type_name, ELSET=context.options.get("elset", self.definition.name))
