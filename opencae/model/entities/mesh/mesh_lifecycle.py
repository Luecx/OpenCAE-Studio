"""Orthogonal provenance, edit, validity and CAD-binding state."""

from dataclasses import dataclass
from enum import StrEnum

from ...core import register_model_type
from ..fem import MeshEntityOrigin


class MeshEditState(StrEnum):
    CLEAN = "Clean"
    MODIFIED = "Modified"
    DETACHED = "Detached"

    @classmethod
    def coerce(cls, value):
        if isinstance(value, cls):
            return value
        text = str(value or cls.CLEAN.value).strip()
        for item in cls:
            if (
                item.value.casefold() == text.casefold()
                or item.name.casefold() == text.casefold()
            ):
                return item
        raise ValueError(f"Unknown mesh edit state: {value!r}")


class MeshValidity(StrEnum):
    CURRENT = "Current"
    OUTDATED = "Outdated"
    INVALID = "Invalid"

    @classmethod
    def coerce(cls, value):
        if isinstance(value, cls):
            return value
        text = str(value or cls.CURRENT.value).strip()
        for item in cls:
            if (
                item.value.casefold() == text.casefold()
                or item.name.casefold() == text.casefold()
            ):
                return item
        raise ValueError(f"Unknown mesh validity: {value!r}")


class GeometryAssociationState(StrEnum):
    NONE = "None"
    ATTACHED = "Attached"
    DETACHED = "Detached"

    @classmethod
    def coerce(cls, value):
        if isinstance(value, cls):
            return value
        text = str(value or cls.NONE.value).strip()
        for item in cls:
            if (
                item.value.casefold() == text.casefold()
                or item.name.casefold() == text.casefold()
            ):
                return item
        raise ValueError(f"Unknown geometry association state: {value!r}")


@register_model_type("mesh_lifecycle_state")
@dataclass
class MeshLifecycleState:
    """Describe mesh state without conflating provenance with validity.

    ``GENERATED`` is the neutral default for a populated mesh reconstructed from
    compact storage. An empty mesh still reports ``Not generated`` through the
    compatibility facade, while the first authored entity explicitly changes
    the origin to ``AUTHORED``.
    """

    origin: MeshEntityOrigin | str = MeshEntityOrigin.GENERATED
    edit_state: MeshEditState | str = MeshEditState.CLEAN
    validity: MeshValidity | str = MeshValidity.CURRENT
    geometry_association: GeometryAssociationState | str = GeometryAssociationState.NONE
    revision: str = ""

    def __post_init__(self) -> None:
        self.origin = MeshEntityOrigin.coerce(self.origin)
        self.edit_state = MeshEditState.coerce(self.edit_state)
        self.validity = MeshValidity.coerce(self.validity)
        self.geometry_association = GeometryAssociationState.coerce(
            self.geometry_association
        )

    def mark_modified(self, *, detached=False) -> None:
        self.edit_state = MeshEditState.DETACHED if detached else MeshEditState.MODIFIED
        if detached:
            self.geometry_association = GeometryAssociationState.DETACHED

    def mark_generated(self, *, revision="", associated=True) -> None:
        self.origin = MeshEntityOrigin.GENERATED
        self.edit_state = MeshEditState.CLEAN
        self.validity = MeshValidity.CURRENT
        self.geometry_association = (
            GeometryAssociationState.ATTACHED
            if associated
            else GeometryAssociationState.NONE
        )
        self.revision = str(revision or "")
