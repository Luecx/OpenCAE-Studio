"""Serializable runtime representation of one input-deck format profile."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import NAMESPACE_URL, uuid4, uuid5


def new_profile_id() -> str:
    """Return a new stable identity for one user-created deck profile."""
    return f"custom:{uuid4()}"


def legacy_profile_id(name: str, format_name: str) -> str:
    """Return a deterministic ID for settings created before profile IDs existed."""
    token = uuid5(NAMESPACE_URL, f"opencae:deck-profile:{format_name}:{name}")
    return f"custom:{token}"


@dataclass(frozen=True)
class DeckRecordProfile:
    """Formatting state and immutable semantic binding for one deck record."""

    template: str
    binding_template: str
    commands: tuple[str, ...] = ()
    enabled: bool = True
    float_format: str = ".6g"

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable record snapshot."""
        return {
            "template": self.template,
            "binding_template": self.binding_template,
            "commands": list(self.commands),
            "enabled": self.enabled,
            "float_format": self.float_format,
        }

    @classmethod
    def from_dict(cls, value: dict) -> "DeckRecordProfile":
        """Build one record profile from persisted settings data."""
        template = str(value.get("template", ""))
        return cls(
            template=template,
            binding_template=str(value.get("binding_template", template)),
            commands=tuple(str(item).upper() for item in value.get("commands", ())),
            enabled=bool(value.get("enabled", True)),
            float_format=str(value.get("float_format", ".6g")),
        )


@dataclass(frozen=True)
class DeckProfile:
    """Complete user-selectable deck formatter profile with stable identity."""

    name: str
    format_name: str
    profile_id: str = field(default_factory=new_profile_id)
    records: dict[str, DeckRecordProfile] = field(default_factory=dict)
    order: dict[str, tuple[str, ...]] = field(default_factory=dict)
    settings: dict[str, object] = field(default_factory=dict)

    def record(self, key: str) -> DeckRecordProfile | None:
        """Return one record by stable tree key."""
        return self.records.get(str(key))

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe profile snapshot suitable for application settings."""
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "format_name": self.format_name,
            "records": {key: value.to_dict() for key, value in self.records.items()},
            "order": {key: list(value) for key, value in self.order.items()},
            "settings": dict(self.settings),
        }

    @classmethod
    def from_dict(cls, value: dict | None) -> "DeckProfile | None":
        """Decode persisted profile data, returning ``None`` for invalid input."""
        if not isinstance(value, dict):
            return None
        name = str(value.get("name", "")).strip()
        format_name = str(value.get("format_name", "")).strip()
        if not name or not format_name:
            return None
        profile_id = str(value.get("profile_id", "")).strip() or legacy_profile_id(
            name, format_name
        )
        records = {
            str(key): DeckRecordProfile.from_dict(item)
            for key, item in dict(value.get("records", {})).items()
            if isinstance(item, dict)
        }
        order = {
            str(key): tuple(str(item) for item in items)
            for key, items in dict(value.get("order", {})).items()
            if isinstance(items, (list, tuple))
        }
        settings = (
            dict(value.get("settings", {}))
            if isinstance(value.get("settings", {}), dict)
            else {}
        )
        return cls(name, format_name, profile_id, records, order, settings)
