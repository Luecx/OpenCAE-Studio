"""Builds reusable label, button, and ribbon-button UI primitives."""

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
from .button_role import ButtonRole
from .button_spec import ButtonSpec
from .label_role import LabelRole
from .label_spec import LabelSpec

RIBBON_LABELS = {
    "Node Set": "NodeSet",
    "Element Set": "ElementSet",
    "Coordinate System": "CSYS",
    "Reference Point": "Ref Point",
}


def label(spec: LabelSpec | str, *, role: LabelRole = LabelRole.BODY) -> QLabel:
    """Create a QLabel using centralized semantic role conventions."""
    resolved = spec if isinstance(spec, LabelSpec) else LabelSpec(str(spec), role)
    widget = QLabel(resolved.text)
    if resolved.role is LabelRole.TITLE:
        widget.setObjectName("PanelTitle")
    elif resolved.role is LabelRole.MUTED:
        widget.setObjectName("MutedLabel")
    elif resolved.role is LabelRole.GROUP:
        widget.setObjectName("GroupLabel")
    if resolved.tooltip:
        widget.setToolTip(resolved.tooltip)
    return widget


def button(
    spec: ButtonSpec | str,
    *,
    role: ButtonRole = ButtonRole.DEFAULT,
    clicked: Callable | None = None,
) -> QPushButton:
    """Create a QPushButton using centralized role and behavior conventions."""
    resolved = spec if isinstance(spec, ButtonSpec) else ButtonSpec(str(spec), role)
    widget = QPushButton(resolved.text)
    if resolved.role is ButtonRole.PRIMARY:
        widget.setObjectName("PrimaryButton")
    elif resolved.role is ButtonRole.DANGER:
        widget.setObjectName("DangerButton")
    if resolved.icon is not None:
        widget.setIcon(resolved.icon)
    widget.setCheckable(resolved.checkable)
    if resolved.tooltip:
        widget.setToolTip(resolved.tooltip)
    if clicked is not None:
        widget.clicked.connect(clicked)
    return widget


def ribbon_label(text: str) -> tuple[str, bool]:
    """Return a compact ribbon caption and whether automatic wrapping is allowed."""
    clean = text.replace("…", "").strip()
    if clean.startswith("New "):
        return "New", False
    if clean.startswith("Duplicate "):
        return "Duplicate", False
    if clean in RIBBON_LABELS:
        return RIBBON_LABELS[clean], False
    return clean, True


def wrapped_ribbon_text(text: str) -> str:
    """Wrap a ribbon caption into at most two visually balanced lines."""
    words = text.replace("…", "").split()
    if len(words) <= 1:
        return text
    if len(words) == 2:
        return "\n".join(words)

    # Splitting around the midpoint gives predictable button heights without
    # relying on Qt's platform-dependent word wrapping inside QToolButton.
    midpoint = (len(words) + 1) // 2
    return " ".join(words[:midpoint]) + "\n" + " ".join(words[midpoint:])


def action_button(action: QAction, *, large: bool = True) -> QToolButton:
    """Create the canonical ribbon/action QToolButton for a QAction."""
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
        # Compact mode is kept only for legacy callers; primary ribbon layouts
        # should prefer semantic group collapsing over mixing visual sizes.
        widget.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        widget.setIconSize(QSize(20, 20))
        widget.setFixedSize(30, 30)
    return widget
