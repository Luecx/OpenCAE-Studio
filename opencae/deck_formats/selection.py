"""Resolve solver-compatible input-deck profiles for analyses and runs."""

from __future__ import annotations

from .profile import DeckProfile


def accepted_formats(adapter) -> tuple[str, ...]:
    """Return deck formats accepted by one solver adapter in preference order."""
    values = tuple(str(item) for item in getattr(adapter, "accepted_deck_formats", ()) if str(item))
    return values or (str(getattr(adapter, "name", "Generic")),)


def default_profile_name(adapter) -> str:
    """Return the immutable built-in profile selected after choosing a solver."""
    return accepted_formats(adapter)[0]


def compatible_profile_names(settings, adapter) -> tuple[str, ...]:
    """Return built-in and persisted custom profiles accepted by ``adapter``."""
    formats = accepted_formats(adapter)
    names = list(formats)
    custom_formats = set(str(item) for item in getattr(adapter, "custom_profile_formats", formats) if str(item))
    for name, raw in settings.deck_profiles.items():
        profile = DeckProfile.from_dict(raw)
        if profile is not None and profile.format_name in formats and profile.format_name in custom_formats and name not in names:
            names.append(name)
    return tuple(names)


def normalized_profile_name(settings, adapter, profile_name: str) -> str:
    """Keep a compatible profile or fall back to the solver's built-in default."""
    name = str(profile_name or "")
    return name if name in compatible_profile_names(settings, adapter) else default_profile_name(adapter)


def resolve_profile(settings, adapter, profile_name: str):
    """Resolve a compatible custom profile; built-ins are represented by ``None``."""
    name = normalized_profile_name(settings, adapter, profile_name)
    if name in accepted_formats(adapter):
        return None
    profile = DeckProfile.from_dict(settings.deck_profiles.get(name))
    if profile is None or profile.format_name not in accepted_formats(adapter):
        return None
    if profile.format_name not in tuple(getattr(adapter, "custom_profile_formats", accepted_formats(adapter))):
        return None
    return profile
