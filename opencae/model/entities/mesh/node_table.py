from dataclasses import dataclass, field

from ...core import SolverWritable, register_model_type


@register_model_type("node_table")
@dataclass
class NodeTable(SolverWritable):
    ids: list[int] = field(default_factory=list)
    coordinates: list[tuple[float, float, float]] = field(default_factory=list)

    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None:
        from opencae.solvers.femaster_dsl.command import command
        command(writer, "NODE", [(node, *point) for node, point in zip(self.ids, self.coordinates)], NSET=context.options.get("nset", "NALL"))
