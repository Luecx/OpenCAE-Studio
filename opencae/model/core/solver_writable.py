from __future__ import annotations

from typing import TYPE_CHECKING

from .solver_name import SolverName

if TYPE_CHECKING:
    from .deck_writer import DeckWriter
    from .export_context import ExportContext


class SolverWritable:
    def write_abaqus(self, writer: "DeckWriter", context: "ExportContext") -> None:
        return None

    def write_femaster(self, writer: "DeckWriter", context: "ExportContext") -> None:
        return None

    def write_generic(self, writer: "DeckWriter", context: "ExportContext") -> None:
        return None

    def write_solver(self, solver: SolverName | str, writer: "DeckWriter", context: "ExportContext") -> None:
        name = SolverName(solver)
        if name is SolverName.ABAQUS:
            self.write_abaqus(writer, context)
        elif name is SolverName.FEMASTER:
            self.write_femaster(writer, context)
        else:
            self.write_generic(writer, context)
