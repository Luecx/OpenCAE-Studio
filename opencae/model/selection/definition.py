from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from opencae.model.core.model_registry import register_model_type
from .operands import RegionOperand, operand_key


@register_model_type("region_selection_item")
@dataclass(frozen=True, slots=True)
class RegionSelectionItem:
    operand: RegionOperand
    picked_position: tuple[float, float, float] | None = None
    display_label: str = ""

    def __post_init__(self):
        if self.picked_position is not None:
            object.__setattr__(self, "picked_position", tuple(float(value) for value in self.picked_position))

    @property
    def key(self) -> tuple: return operand_key(self.operand)


@register_model_type("region_definition")
@dataclass(frozen=True, slots=True)
class RegionDefinition:
    items: tuple[RegionSelectionItem, ...] = field(default_factory=tuple)

    def __post_init__(self):
        unique = {}
        for value in self.items:
            item = value if isinstance(value, RegionSelectionItem) else RegionSelectionItem(value)
            unique.setdefault(item.key, item)
        object.__setattr__(self, "items", tuple(unique.values()))

    @property
    def empty(self) -> bool: return not self.items
    @property
    def operands(self) -> tuple[RegionOperand, ...]: return tuple(item.operand for item in self.items)

    def add(self, *values) -> "RegionDefinition":
        return RegionDefinition((*self.items, *(as_selection_item(value) for value in values)))

    def remove_keys(self, keys: Iterable[tuple]) -> "RegionDefinition":
        unwanted = set(keys)
        return RegionDefinition(tuple(item for item in self.items if item.key not in unwanted))

    @classmethod
    def from_values(cls, values=()) -> "RegionDefinition":
        if isinstance(values, RegionDefinition): return values
        return cls(tuple(as_selection_item(value) for value in (values or ())))


def as_selection_item(value) -> RegionSelectionItem:
    if isinstance(value, RegionSelectionItem): return value
    return RegionSelectionItem(value)
