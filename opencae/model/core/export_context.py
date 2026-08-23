"""Provides current Project resolution and stable solver naming during export."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .export_names import ExportNameRegistry
from .reference import EntityRef


@dataclass
class ExportContext:
    """Runtime context shared by solver exporter components."""

    project: Any
    analysis: Any | None = None
    options: dict[str, Any] = field(default_factory=dict)
    names: ExportNameRegistry = field(default_factory=ExportNameRegistry)

    def resolve(self, ref, expected_type=None):
        """Resolve one current Project reference."""
        return (
            self.project.try_resolve(ref, expected_type)
            if hasattr(self.project, "try_resolve")
            else None
        )

    def current_name(self, ref, fallback: str = "") -> str:
        """Return the current entity name or the explicit fallback."""
        entity = self.resolve(ref)
        return entity.name if entity is not None else fallback

    def solver_name(
        self,
        entity_or_ref,
        proposed: str | None = None,
        key=None,
    ) -> str:
        """Register and return one stable solver-facing name."""
        entity = (
            self.resolve(entity_or_ref)
            if isinstance(entity_or_ref, EntityRef)
            else entity_or_ref
        )
        if entity is not None and hasattr(entity, "id"):
            return self.names.register(
                key if key is not None else entity.id,
                proposed or entity.name,
            )
        fallback = proposed or self.current_name(entity_or_ref, "ENTITY")
        return self.names.register(
            key if key is not None else ("raw", fallback),
            fallback,
        )
