"""Canonical low-level OpenCAE UI primitives.

This package owns reusable interaction controls. Higher-level templates,
composites, dialogs, ribbons, and workspaces should compose these primitives
instead of constructing raw Qt buttons repeatedly.
"""

from .buttons import (
    ActionButton,
    ButtonPresentation,
    ChoiceButton,
    FormButton,
    InlineButton,
    MenuButton,
    OptionsButton,
    SplitButton,
    ToggleButton,
    ViewportButton,
)
from .semantic_label import SemanticLabel

__all__ = [
    "ActionButton",
    "ButtonPresentation",
    "ChoiceButton",
    "FormButton",
    "InlineButton",
    "MenuButton",
    "OptionsButton",
    "SemanticLabel",
    "SplitButton",
    "ToggleButton",
    "ViewportButton",
]
