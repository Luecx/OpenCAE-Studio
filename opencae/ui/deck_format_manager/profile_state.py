"""Bridge editable deck-manager state to solver-independent runtime profiles."""

from __future__ import annotations

from opencae.deck_formats import DeckProfile, DeckRecordProfile, new_profile_id

from .catalog import template_spec
from .template_catalog import TEMPLATE_SPECS


def record_states_from_profile(profile: DeckProfile) -> dict[str, dict[str, object]]:
    """Return UI record states from one persisted runtime profile."""
    return {
        key: {
            "template": record.template,
            "enabled": record.enabled,
            "float_format": record.float_format,
        }
        for key, record in profile.records.items()
    }


def build_profile(
    name: str,
    format_name: str,
    record_states: dict[str, dict[str, object]],
    order: dict[str, tuple[str, ...]],
    settings: dict[str, object],
    supported: dict[str, bool] | None = None,
    *,
    profile_id: str = "",
) -> DeckProfile:
    """Build a complete runtime profile from current editor state.

    ``binding_template`` is always the immutable native template for the selected
    format. User edits alter rendering only, never the semantic binding contract.
    """
    support = supported or {}
    records: dict[str, DeckRecordProfile] = {}
    for key in TEMPLATE_SPECS:
        spec = template_spec(key, format_name=format_name)
        state = dict(record_states.get(key, {}))
        allowed = bool(support.get(key, True))
        records[key] = DeckRecordProfile(
            template=str(state.get("template", spec["template"])),
            binding_template=str(spec["template"]),
            commands=tuple(str(item).upper() for item in spec.get("commands", ())),
            enabled=bool(state.get("enabled", spec.get("enabled", True))) and allowed,
            float_format=str(state.get("float_format", ".6g")),
        )
    return DeckProfile(
        name=str(name),
        format_name=str(format_name),
        profile_id=str(profile_id or new_profile_id()),
        records=records,
        order={key: tuple(values) for key, values in order.items()},
        settings=dict(settings),
    )
