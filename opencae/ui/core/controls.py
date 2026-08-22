from __future__ import annotations

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QDialogButtonBox, QPushButton, QToolButton

from opencae.ui.templates.dialogs import dialog_buttons as _dialog_buttons
from opencae.ui.templates.menus import action_group_button as _action_group_button
from opencae.ui.templates.primitives import action_button as _action_button, button as _button
from opencae.ui.templates.specs import ButtonRole


def primary_button(text: str) -> QPushButton:
    return _button(text, role=ButtonRole.PRIMARY)


def dialog_buttons(include_apply: bool = False) -> QDialogButtonBox:
    return _dialog_buttons(include_apply=include_apply)


def action_button(action: QAction, large: bool = True) -> QToolButton:
    return _action_button(action, large=large)


def action_group_button(
    text: str,
    icon_action: QAction,
    menu_actions: tuple[QAction, ...],
) -> QToolButton:
    return _action_group_button(text, icon_action, menu_actions)
