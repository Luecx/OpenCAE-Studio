from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QDialogButtonBox, QPushButton, QToolButton

from .metrics import RIBBON_BUTTON_HEIGHT, RIBBON_BUTTON_WIDTH, RIBBON_ICON_SIZE

RIBBON_COMPACT_BUTTON_SIZE = 37
RIBBON_COMPACT_ICON_SIZE = 20


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
    button.setProperty("ribbonButton", True)
    if large:
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setIconSize(QSize(RIBBON_ICON_SIZE, RIBBON_ICON_SIZE))
        button.setFixedSize(RIBBON_BUTTON_WIDTH, RIBBON_BUTTON_HEIGHT)
        button.setText(_ribbon_text(action.text()))
    else:
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        button.setIconSize(
            QSize(RIBBON_COMPACT_ICON_SIZE, RIBBON_COMPACT_ICON_SIZE)
        )
        button.setFixedSize(
            RIBBON_COMPACT_BUTTON_SIZE,
            RIBBON_COMPACT_BUTTON_SIZE,
        )
        button.setToolTip(action.text().replace("…", ""))
        button.setProperty("compactRibbonButton", True)
    return button
