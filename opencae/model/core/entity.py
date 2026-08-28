"""Defines the persistent identity base class for OpenCAE model entities."""

from __future__ import annotations

from dataclasses import dataclass, field, is_dataclass
from typing import Any

from opencae.core.ids import new_id

from .model_codec import encode_model
from .persistent_model_field import is_persistent_model_field
from .solver_writable import SolverWritable


_MISSING = object()


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
        """Protect identity and invalidate graph indexes only for structural changes.

        ProjectIndex contains ownership paths, Entity identities and EntityRef
        relationships. Scalar metadata such as names, lifecycle status, progress,
        timestamps and numeric settings do not change any of those structures, so
        invalidating the entire index for every such assignment is unnecessary and
        particularly expensive for large FE models.
        """
        if name == "id" and "id" in self.__dict__ and self.__dict__["id"] != value:
            raise AttributeError("Entity.id is immutable")

        previous = self.__dict__.get(name, _MISSING)
        super().__setattr__(name, value)

        project = self.__dict__.get("_project")
        if project is None:
            return
        field_info = getattr(type(self), "__dataclass_fields__", {}).get(name)
        if field_info is None or not is_persistent_model_field(field_info):
            return
        if not (
            _may_affect_project_index(previous)
            or _may_affect_project_index(value)
        ):
            return
        invalidate = getattr(project, "invalidate_index", None)
        if callable(invalidate):
            invalidate()

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


def _may_affect_project_index(value: Any) -> bool:
    """Return whether assigning ``value`` can alter ownership/reference topology."""
    if value is _MISSING or value is None:
        return False
    # Entity, EntityRef and nested model records are dataclasses. Collections can
    # own or contain any of those. Scalars cannot affect ProjectIndex structure.
    return is_dataclass(value) or isinstance(value, (list, tuple, dict))
