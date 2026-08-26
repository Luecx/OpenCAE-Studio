"""Solver-independent input-deck profile runtime support."""

from .profile import DeckProfile, DeckRecordProfile, new_profile_id
from .selection import (
    accepted_formats,
    builtin_profile_id,
    compatible_profile_ids,
    compatible_profile_names,
    default_profile_id,
    normalized_profile_id,
    profile_choices,
    profile_display_name,
    resolve_profile,
)
from .template_language import render_template
from .writer import ProfileCommandWriter

__all__ = [
    "DeckProfile",
    "DeckRecordProfile",
    "ProfileCommandWriter",
    "accepted_formats",
    "builtin_profile_id",
    "compatible_profile_ids",
    "compatible_profile_names",
    "default_profile_id",
    "new_profile_id",
    "normalized_profile_id",
    "profile_choices",
    "profile_display_name",
    "resolve_profile",
    "render_template",
]
