"""Compatibility factories backed by structurally named UI primitives."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QLabel, QPushButton, QToolButton

from opencae.ui.primitives.buttons import ActionButton, ButtonPresentation
from opencae.ui.primitives.buttons.button_form_action import ButtonFormAction
from opencae.ui.primitives.buttons.button_form_danger import ButtonFormDanger
from opencae.ui.primitives.buttons.button_form_primary import ButtonFormPrimary
from opencae.ui.primitives.buttons.button_form_toggle import ButtonFormToggle
from opencae.ui.primitives.buttons.button_ribbon_action import ButtonRibbonAction
from opencae.ui.primitives.buttons.button_ribbon_menu import ButtonRibbonMenu
from opencae.ui.primitives.buttons.button_ribbon_toggle import ButtonRibbonToggle
from opencae.ui.primitives.ribbon_text import ribbon_label, wrapped_ribbon_text
from opencae.ui.primitives.semantic_label import SemanticLabel

from .button_role import ButtonRole
from .button_spec import ButtonSpec
from .label_role import LabelRole
from .label_spec import LabelSpec


def label(spec: LabelSpec | str, *, role: LabelRole = LabelRole.BODY) -> QLabel:
    return SemanticLabel(spec, role=role)


def button(
    spec: ButtonSpec | str,
    *,
    role: ButtonRole = ButtonRole.DEFAULT,
    clicked: Callable | None = None,
) -> QPushButton:
    resolved = spec if isinstance(spec, ButtonSpec) else ButtonSpec(str(spec), role)
    if resolved.checkable:
        widget = ButtonFormToggle(
            resolved.text,
            icon=resolved.icon,
            tooltip=resolved.tooltip,
        )
    elif resolved.role is ButtonRole.PRIMARY:
        widget = ButtonFormPrimary(resolved.text)
    elif resolved.role is ButtonRole.DANGER:
        widget = ButtonFormDanger(resolved.text)
    else:
        widget = ButtonFormAction(
            resolved.text,
            icon=resolved.icon,
            tooltip=resolved.tooltip,
        )
    if clicked is not None:
        widget.clicked.connect(clicked)
    return widget


def action_button(action: QAction, *, large: bool = True) -> QToolButton:
    if large:
        if action.menu() is not None:
            return ButtonRibbonMenu(action)
        if action.isCheckable():
            return ButtonRibbonToggle(action)
        return ButtonRibbonAction(action)

    # Compact is a retained compatibility-only surface.  New code should use a
    # structurally named concrete primitive for its actual host surface.
    return ActionButton(action, presentation=ButtonPresentation.COMPACT)


__all__ = [
    "action_button",
    "button",
    "label",
    "ribbon_label",
    "wrapped_ribbon_text",
]
