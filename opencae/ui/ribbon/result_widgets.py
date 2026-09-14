from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QFrame

from opencae.ui.core.icon_factory import make_icon
from opencae.ui.primitives.buttons import (
    ActionButton,
    ButtonPresentation,
    ToggleButton,
    button_for_action,
)


def ribbon_button(text, icon, checked=False, width=76):
    icon_value = make_icon(icon, 28)
    if checked is None:
        button = ActionButton(
            text=text,
            icon=icon_value,
            presentation=ButtonPresentation.RIBBON,
        )
    else:
        button = ToggleButton(
            text=text,
            icon=icon_value,
            checked=checked,
            presentation=ButtonPresentation.RIBBON,
        )
    # Results intentionally retain their denser historic ribbon geometry.
    button.setIconSize(QSize(28, 28))
    button.setFixedSize(width, 70)
    return button


def action_button(action, width=76):
    button = button_for_action(action, presentation=ButtonPresentation.RIBBON)
    button.setIconSize(QSize(28, 28))
    button.setFixedSize(width, 70)
    return button


def vertical_separator():
    line = QFrame()
    line.setFrameShape(QFrame.Shape.VLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    line.setFixedWidth(10)
    line.setContentsMargins(4, 8, 4, 8)
    return line
