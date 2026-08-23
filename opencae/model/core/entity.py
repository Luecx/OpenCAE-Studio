"""Defines the persistent identity base class for OpenCAE model entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from opencae.core.ids import new_id

from .model_codec import encode_model
from .solver_writable import SolverWritable


@dataclass
class Entity(SolverWritable):
    """Base class for persistent model entities with immutable stable identity.

    ``id`` is persistence identity. User-facing relationships are normal object
    references; the owning Project is attached only at runtime and is never
    serialized.
    """

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

    def __setattr__(self, name, value) -> None:
        """Prevent stable entity identity from changing after construction."""
        if name == "id" and "id" in self.__dict__ and self.__dict__["id"] != value:
            raise AttributeError("Entity.id is immutable")
        super().__setattr__(name, value)

    @property
    def project(self):
        """Return the runtime Project currently owning this Entity."""
        return self._project

    def _bind_project(self, project) -> None:
        """Bind this Entity to a Project and invalidate resolved-object caches."""
        # deepcopy/undo can copy a descriptor cache pointing into an older graph.
        # Clearing it here guarantees every object alias resolves in the newly
        # indexed Project even when the referenced ID happens to be identical.
        for key in tuple(self.__dict__):
            if key.startswith("_resolved_"):
                self.__dict__.pop(key, None)
        self._project = project

    def resolve_reference(self, ref, expected_type=None):
        """Resolve a persisted reference through the runtime owning Project."""
        if self._project is None:
            return None
        return self._project.try_resolve(ref, expected_type)

    def to_dict(self) -> dict[str, Any]:
        """Encode this entity graph using the registered model codec."""
        return encode_model(self)
