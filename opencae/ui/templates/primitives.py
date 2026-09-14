"""Compatibility factories backed by canonical semantic UI primitives."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QLabel, QPushButton, QToolButton

from opencae.ui.primitives.buttons import (
    ActionButton,
    ButtonPresentation,
    FormButton,
    MenuButton,
    ToggleButton,
)
from opencae.ui.primitives.ribbon_text import ribbon_label, wrapped_ribbon_text
from opencae.ui.primitives.semantic_label import SemanticLabel

from .button_role import ButtonRole
from .button_spec import ButtonSpec
from .label_role import LabelRole
from .label_spec import LabelSpec


def label(spec: LabelSpec | str, *, role: LabelRole = LabelRole.BODY) -> QLabel:
    """Create a semantic label through the canonical primitive class."""
    return SemanticLabel(spec, role=role)


def button(
    spec: ButtonSpec | str,
    *,
    role: ButtonRole = ButtonRole.DEFAULT,
    clicked: Callable | None = None,
) -> QPushButton:
    """Create a semantic form button through the canonical primitive class."""
    return FormButton(spec, role=role, clicked=clicked)


def action_button(action: QAction, *, large: bool = True) -> QToolButton:
    """Create the canonical QAction button for ribbon or compact presentation.

    The QAction describes behavior.  The primitive class describes the
    interaction kind, while ``ButtonPresentation`` controls only geometry and
    surface styling.  This keeps menu/toggle semantics independent from whether
    a control is shown in a ribbon, compact overflow or another host.
    """
    presentation = (
        ButtonPresentation.RIBBON if large else ButtonPresentation.COMPACT
    )
    if action.menu() is not None:
        return MenuButton(action=action, presentation=presentation)
    if action.isCheckable():
        return ToggleButton(action, presentation=presentation)
    return ActionButton(action, presentation=presentation)


__all__ = [
    "action_button",
    "button",
    "label",
    "ribbon_label",
    "wrapped_ribbon_text",
]
