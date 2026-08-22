from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QDialogButtonBox,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QToolButton,
    QWidget,
    QWidgetAction,
)

from .metrics import RIBBON_BUTTON_HEIGHT, RIBBON_BUTTON_WIDTH, RIBBON_ICON_SIZE


def primary_button(text: str) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("PrimaryButton")
    return button


def dialog_buttons(include_apply: bool = False) -> QDialogButtonBox:
    flags = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    if include_apply:
        flags |= QDialogButtonBox.StandardButton.Apply
    buttons = QDialogButtonBox(flags)
    ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
    if ok_button is not None:
        ok_button.setObjectName("PrimaryButton")
    return buttons


def _ribbon_text(text: str) -> str:
    words = text.replace("…", "").split()
    if len(words) <= 1:
        return text
    if len(words) == 2:
        return "\n".join(words)
    midpoint = (len(words) + 1) // 2
    return " ".join(words[:midpoint]) + "\n" + " ".join(words[midpoint:])


def action_button(action: QAction, large: bool = True) -> QToolButton:
    button = QToolButton()
    button.setDefaultAction(action)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    if large:
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setIconSize(QSize(RIBBON_ICON_SIZE, RIBBON_ICON_SIZE))
        button.setFixedSize(RIBBON_BUTTON_WIDTH, RIBBON_BUTTON_HEIGHT)
        button.setText(_ribbon_text(action.text()))
        button.setProperty("ribbonButton", True)
    else:
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        button.setIconSize(QSize(20, 20))
        button.setFixedSize(30, 30)
    return button


def action_group_button(
    text: str,
    icon_action: QAction,
    menu_actions: tuple[QAction, ...],
) -> QToolButton:
    """Create one large ribbon button that expands a row of full-size actions."""
    button = QToolButton()
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
    button.setIcon(icon_action.icon())
    button.setIconSize(QSize(RIBBON_ICON_SIZE, RIBBON_ICON_SIZE))
    button.setFixedSize(RIBBON_BUTTON_WIDTH, RIBBON_BUTTON_HEIGHT)
    button.setText(_ribbon_text(text))
    button.setProperty("ribbonButton", True)

    menu = QMenu(button)
    panel = QWidget(menu)
    row = QHBoxLayout(panel)
    row.setContentsMargins(6, 6, 6, 6)
    row.setSpacing(2)

    for action in menu_actions:
        action_widget = action_button(action)
        action_widget.clicked.connect(menu.close)
        row.addWidget(action_widget)

    widget_action = QWidgetAction(menu)
    widget_action.setDefaultWidget(panel)
    menu.addAction(widget_action)

    button.setMenu(menu)
    button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    return button
