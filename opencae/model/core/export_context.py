from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .export_names import ExportNameRegistry
from .reference import EntityRef


@dataclass
class ExportContext:
    project: Any
    analysis: Any | None = None
    options: dict[str, Any] = field(default_factory=dict)
    names: ExportNameRegistry = field(default_factory=ExportNameRegistry)

    def resolve(self, ref, expected_type=None):
        return self.project.try_resolve(ref, expected_type) if hasattr(self.project, "try_resolve") else None

    def current_name(self, ref, fallback: str = "") -> str:
        entity = self.resolve(ref)
        if entity is not None: return entity.name
        if isinstance(ref, EntityRef): return ref.legacy_name or fallback
        return fallback

    def solver_name(self, entity_or_ref, proposed: str | None = None, key=None) -> str:
        entity = self.resolve(entity_or_ref) if isinstance(entity_or_ref, EntityRef) else entity_or_ref
        if entity is not None and hasattr(entity, "id"):
            return self.names.register(key if key is not None else entity.id, proposed or entity.name)
        fallback = proposed or self.current_name(entity_or_ref, "ENTITY")
        return self.names.register(key if key is not None else ("raw", fallback), fallback)
