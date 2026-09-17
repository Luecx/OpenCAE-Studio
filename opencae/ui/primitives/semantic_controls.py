"""Create semantic labels and buttons from typed presentation specifications."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtWidgets import QLabel, QPushButton

from opencae.ui.primitives.buttons.button_form_action import ButtonFormAction
from opencae.ui.primitives.buttons.button_form_danger import ButtonFormDanger
from opencae.ui.primitives.buttons.button_form_primary import ButtonFormPrimary
from opencae.ui.primitives.buttons.button_form_toggle import ButtonFormToggle
from opencae.ui.primitives.labels import LabelBody, LabelGroup, LabelMuted, LabelTitle

from .buttons.button_role import ButtonRole
from .buttons.button_spec import ButtonSpec
from .label_role import LabelRole
from .label_spec import LabelSpec


def label(spec: LabelSpec | str, *, role: LabelRole = LabelRole.BODY) -> QLabel:
    resolved = spec if isinstance(spec, LabelSpec) else LabelSpec(str(spec), role)
    if resolved.role is LabelRole.TITLE:
        widget = LabelTitle(resolved.text)
    elif resolved.role is LabelRole.MUTED:
        widget = LabelMuted(resolved.text)
    elif resolved.role is LabelRole.GROUP:
        widget = LabelGroup(resolved.text)
    else:
        widget = LabelBody(resolved.text)
    if resolved.tooltip:
        widget.setToolTip(resolved.tooltip)
    return widget


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


__all__ = [
    "button",
    "label",
]
