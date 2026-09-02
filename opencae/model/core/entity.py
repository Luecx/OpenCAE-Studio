"""Defines the persistent identity base class for OpenCAE model entities."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from opencae.core.ids import new_id

from .model_codec import encode_model
from .persistent_model_field import is_persistent_model_field
from .project_index_impact import value_affects_project_index
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
    metadata: dict[str, Any] = field(
        default_factory=dict,
        metadata={"project_index": False},
    )
    _project: Any = field(
        init=False,
        default=None,
        repr=False,
        compare=False,
        metadata={"serialize": False},
    )

    def __deepcopy__(self, memo):
        """Copy entity state without following runtime Project/index backreferences.

        Every indexed Entity is bound to its owning Project. Python's default
        ``deepcopy`` follows that runtime link, so copying a tiny Seed or Step can
        otherwise clone an entire 400k-element model. Command/history copies are
        detached values: persistent/non-graph runtime state is copied normally,
        while Project ownership, resolved caches, and a root Project's runtime
        index are rebuilt only when the copy is inserted into a live graph.
        """
        existing = memo.get(id(self))
        if existing is not None:
            return existing
        clone = type(self).__new__(type(self))
        memo[id(self)] = clone
        for name, value in self.__dict__.items():
            if name in {"_project", "_index"} or name.startswith("_resolved_"):
                continue
            object.__setattr__(clone, name, deepcopy(value, memo))
        object.__setattr__(clone, "_project", None)
        if "_index" in getattr(type(self), "__dataclass_fields__", {}):
            object.__setattr__(clone, "_index", None)
        return clone

    def __setattr__(self, name, value) -> None:
        """Protect identity and invalidate graph indexes only for structural changes.

        ProjectIndex contains ownership paths, Entity identities and EntityRef
        relationships. Scalar metadata, numeric tuples and reference-free model
        records do not change those structures, so they must not invalidate the
        entire index on every edit.
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
        if field_info.metadata.get("project_index", True) is False:
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
    if value is _MISSING:
        return False
    return value_affects_project_index(value)
