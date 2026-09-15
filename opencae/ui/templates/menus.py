"""Compatibility factories for menu-based UI composites."""

from __future__ import annotations

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QToolButton

from opencae.ui.composites import CollapsedActionGroupButton


def action_group_button(
    text: str,
    icon_action: QAction,
    menu_actions: tuple[QAction, ...],
) -> QToolButton:
    """Create the canonical collapsed ribbon action-group composite."""
    return CollapsedActionGroupButton(text, icon_action, menu_actions)
