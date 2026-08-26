"""Resolve solver-compatible input-deck profiles for analyses and runs."""

from __future__ import annotations

from .profile import DeckProfile


_BUILTIN_IDS = {
    "FEMaster": "builtin:femaster",
    "Abaqus": "builtin:abaqus",
}


def accepted_formats(adapter) -> tuple[str, ...]:
    """Return deck formats accepted by one solver adapter in preference order."""
    values = tuple(
        str(item)
        for item in getattr(adapter, "accepted_deck_formats", ())
        if str(item)
    )
    return values or (str(getattr(adapter, "name", "Generic")),)


def builtin_profile_id(format_name: str) -> str:
    """Return the stable identity of one immutable built-in deck profile."""
    name = str(format_name)
    return _BUILTIN_IDS.get(name, f"builtin:{name.casefold()}")


def default_profile_id(adapter) -> str:
    """Return the solver's preferred immutable built-in profile identity."""
    return builtin_profile_id(accepted_formats(adapter)[0])


def profile_choices(settings, adapter) -> tuple[tuple[str, str], ...]:
    """Return ``(profile_id, display_name)`` choices accepted by ``adapter``."""
    formats = accepted_formats(adapter)
    choices = [(builtin_profile_id(name), name) for name in formats]
    custom_formats = set(
        str(item)
        for item in getattr(adapter, "custom_profile_formats", formats)
        if str(item)
    )
    seen = {profile_id for profile_id, _name in choices}
    for raw in settings.deck_profiles.values():
        profile = DeckProfile.from_dict(raw)
        if (
            profile is not None
            and profile.format_name in formats
            and profile.format_name in custom_formats
            and profile.profile_id not in seen
        ):
            choices.append((profile.profile_id, profile.name))
            seen.add(profile.profile_id)
    return tuple(choices)


def compatible_profile_ids(settings, adapter) -> tuple[str, ...]:
    """Return stable IDs of every profile accepted by one solver adapter."""
    return tuple(profile_id for profile_id, _name in profile_choices(settings, adapter))


def compatible_profile_names(settings, adapter) -> tuple[str, ...]:
    """Return display names of every profile accepted by one solver adapter."""
    return tuple(name for _profile_id, name in profile_choices(settings, adapter))


def normalized_profile_id(settings, adapter, profile_id: str) -> str:
    """Keep a compatible identity or fall back to the solver's built-in profile."""
    value = str(profile_id or "")
    return value if value in compatible_profile_ids(settings, adapter) else default_profile_id(adapter)


def profile_display_name(settings, profile_id: str) -> str:
    """Return a human-readable name for one built-in or custom profile identity."""
    value = str(profile_id or "")
    for format_name, builtin_id in _BUILTIN_IDS.items():
        if value == builtin_id:
            return format_name
    for raw in settings.deck_profiles.values():
        profile = DeckProfile.from_dict(raw)
        if profile is not None and profile.profile_id == value:
            return profile.name
    return value


def resolve_profile(settings, adapter, profile_id: str):
    """Resolve a compatible custom profile; built-ins are represented by ``None``."""
    selected = normalized_profile_id(settings, adapter, profile_id)
    if selected in {builtin_profile_id(name) for name in accepted_formats(adapter)}:
        return None
    for raw in settings.deck_profiles.values():
        profile = DeckProfile.from_dict(raw)
        if profile is None or profile.profile_id != selected:
            continue
        if profile.format_name not in accepted_formats(adapter):
            return None
        custom_formats = tuple(
            getattr(adapter, "custom_profile_formats", accepted_formats(adapter))
        )
        return profile if profile.format_name in custom_formats else None
    return None
