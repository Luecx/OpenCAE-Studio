from __future__ import annotations

from dataclasses import dataclass

from dataclasses import replace

from .types import SelectableKind, SelectionOperation


@dataclass(frozen=True, slots=True)
class ViewportHit:
    """One immutable, typed viewport pick.

    Rendering adapters create hits; controllers and region tools consume them.
    UI labels are descriptive only and never participate in identity.
    """

    kind: SelectableKind
    entity_id: str | None = None
    instance_id: str | None = None
    owner_id: str | None = None
    topology_tag: int | None = None
    mesh_id: int | None = None
    local_face: str | None = None
    world_position: tuple[float, float, float] | None = None
    dimension: int | None = None
    label: str = ""
    selection_operation: SelectionOperation = SelectionOperation.ADD

    @property
    def key(self) -> tuple:
        return (
            self.kind,
            self.instance_id or "",
            self.owner_id or "",
            self.entity_id or "",
            self.topology_tag,
            self.mesh_id,
            self.local_face or "",
        )

    def with_operation(self, operation: SelectionOperation | str) -> "ViewportHit":
        return replace(self, selection_operation=SelectionOperation(operation))




@dataclass(frozen=True, slots=True)
class ViewportSelection:
    """Typed transient viewport selection used by the normal model UI."""

    hits: tuple[ViewportHit, ...] = ()

    @property
    def name(self) -> str:
        return self.hits[0].label if self.hits else ""

    @property
    def empty(self) -> bool:
        return not self.hits

    @classmethod
    def from_hits(cls, values) -> "ViewportSelection":
        hits = tuple(values or ())
        invalid = [type(value).__name__ for value in hits if not isinstance(value, ViewportHit)]
        if invalid:
            raise TypeError(f"ViewportSelection requires ViewportHit values, got {', '.join(invalid)}")
        return cls(hits)
