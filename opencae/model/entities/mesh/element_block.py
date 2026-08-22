from __future__ import annotations

from dataclasses import dataclass, field

from ...core import SolverWritable, register_model_type
from ..elements.base import ElementDefinition
from ..fem import Element


@register_model_type("element_block")
@dataclass
class ElementBlock(SolverWritable):
    """Compact storage for elements sharing one solver element definition."""

    definition: ElementDefinition
    ids: list[int] = field(default_factory=list)
    connectivity: list[tuple[int, ...]] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.ids)

    def add(self, element: Element) -> None:
        if not isinstance(element, Element):
            raise TypeError("ElementBlock.add expects an Element object")
        if not isinstance(self.definition, element.definition_type):
            raise TypeError(
                f"{type(element).__name__} is incompatible with "
                f"{type(self.definition).__name__}"
            )
        if element.id in self.ids:
            raise ValueError(f"Element id {element.id} already exists in block")
        self.ids.append(element.id)
        self.connectivity.append(element.connectivity)
        self.definition.count = len(self.ids)

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
