from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QLabel, QPushButton, QToolButton

from opencae.ui.core.metrics import (
    RIBBON_BUTTON_HEIGHT,
    RIBBON_BUTTON_WIDTH,
    RIBBON_ICON_SIZE,
)
from .specs import ButtonRole, ButtonSpec, LabelRole, LabelSpec


RIBBON_LABELS = {
    "Node Set": "NodeSet",
    "Element Set": "ElementSet",
    "Coordinate System": "CSYS",
    "Reference Point": "Ref Point",
}


def label(spec: LabelSpec | str, *, role: LabelRole = LabelRole.BODY) -> QLabel:
    spec = spec if isinstance(spec, LabelSpec) else LabelSpec(str(spec), role)
    widget = QLabel(spec.text)
    if spec.role == LabelRole.TITLE:
        widget.setObjectName("PanelTitle")
    elif spec.role == LabelRole.MUTED:
        widget.setObjectName("MutedLabel")
    elif spec.role == LabelRole.GROUP:
        widget.setObjectName("GroupLabel")
    if spec.tooltip:
        widget.setToolTip(spec.tooltip)
    return widget


def button(
    spec: ButtonSpec | str,
    *,
    role: ButtonRole = ButtonRole.DEFAULT,
    clicked: Callable | None = None,
) -> QPushButton:
    spec = spec if isinstance(spec, ButtonSpec) else ButtonSpec(str(spec), role)
    widget = QPushButton(spec.text)
    if spec.role == ButtonRole.PRIMARY:
        widget.setObjectName("PrimaryButton")
    elif spec.role == ButtonRole.DANGER:
        widget.setObjectName("DangerButton")
    if spec.icon is not None:
        widget.setIcon(spec.icon)
    widget.setCheckable(spec.checkable)
    if spec.tooltip:
        widget.setToolTip(spec.tooltip)
    if clicked is not None:
        widget.clicked.connect(clicked)
    return widget


def ribbon_label(text: str) -> tuple[str, bool]:
    clean = text.replace("…", "").strip()
    if clean.startswith("New "):
        return "New", False
    if clean.startswith("Duplicate "):
        return "Duplicate", False
    if clean in RIBBON_LABELS:
        return RIBBON_LABELS[clean], False
    return clean, True


def wrapped_ribbon_text(text: str) -> str:
    words = text.replace("…", "").split()
    if len(words) <= 1:
        return text
    if len(words) == 2:
        return "\n".join(words)
    midpoint = (len(words) + 1) // 2
    return " ".join(words[:midpoint]) + "\n" + " ".join(words[midpoint:])


def action_button(action: QAction, *, large: bool = True) -> QToolButton:
    widget = QToolButton()
    widget.setDefaultAction(action)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if large:
        text, may_wrap = ribbon_label(action.text())
        widget.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        widget.setIconSize(QSize(RIBBON_ICON_SIZE, RIBBON_ICON_SIZE))
        widget.setFixedSize(RIBBON_BUTTON_WIDTH, RIBBON_BUTTON_HEIGHT)
        widget.setText(wrapped_ribbon_text(text) if may_wrap else text)
        widget.setProperty("ribbonButton", True)
    else:
        widget.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        widget.setIconSize(QSize(20, 20))
        widget.setFixedSize(30, 30)
    return widget
