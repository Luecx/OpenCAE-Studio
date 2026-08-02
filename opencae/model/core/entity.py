from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from opencae.core.ids import new_id

from .model_codec import encode_model
from .solver_writable import SolverWritable


@dataclass
class Entity(SolverWritable):
    def __setattr__(self, name, value):
        if name == "id" and "id" in self.__dict__ and self.__dict__["id"] != value:
            raise AttributeError("Entity.id is immutable")
        super().__setattr__(name, value)

    name: str
    id: str = field(default_factory=lambda: new_id("entity"))
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return encode_model(self)
