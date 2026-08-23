"""Compatibility facade for canonical OpenCAE UI control templates."""

from __future__ import annotations

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QDialogButtonBox, QPushButton, QToolButton

from opencae.ui.templates.button_role import ButtonRole
from opencae.ui.templates.dialogs import dialog_buttons as _dialog_buttons
from opencae.ui.templates.menus import action_group_button as _action_group_button
from opencae.ui.templates.primitives import action_button as _action_button, button as _button


def primary_button(text: str) -> QPushButton:
    """Create a canonical primary push button for legacy callers."""
    return _button(text, role=ButtonRole.PRIMARY)


def dialog_buttons(include_apply: bool = False) -> QDialogButtonBox:
    """Create the canonical dialog button box for legacy callers."""
    return _dialog_buttons(include_apply=include_apply)


def action_button(action: QAction, large: bool = True) -> QToolButton:
    """Create a canonical action button for legacy callers."""
    return _action_button(action, large=large)


def action_group_button(
    text: str,
    icon_action: QAction,
    menu_actions: tuple[QAction, ...],
) -> QToolButton:
    """Create a canonical collapsed ribbon-group button for legacy callers."""
    return _action_group_button(text, icon_action, menu_actions)
