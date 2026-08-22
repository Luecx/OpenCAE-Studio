from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from opencae.core.ids import new_id

from .model_codec import encode_model
from .solver_writable import SolverWritable


@dataclass
class Entity(SolverWritable):
    """Base class for persistent model entities.

    ``id`` is persistence identity. User-facing relationships are normal object
    references; the owning project is attached at runtime and is never serialized.
    """

    def __setattr__(self, name, value):
        if name == "id" and "id" in self.__dict__ and self.__dict__["id"] != value:
            raise AttributeError("Entity.id is immutable")
        super().__setattr__(name, value)

    name: str
    id: str = field(default_factory=lambda: new_id("entity"))
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    _project: Any = field(
        init=False,
        default=None,
        repr=False,
        compare=False,
        metadata={"serialize": False},
    )

    @property
    def project(self):
        return self._project

    def _bind_project(self, project) -> None:
        self._project = project

    def resolve_reference(self, ref, expected_type=None):
        if self._project is None:
            return None
        return self._project.try_resolve(ref, expected_type)

    def to_dict(self) -> dict[str, Any]:
        return encode_model(self)
