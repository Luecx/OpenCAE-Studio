"""Compatibility factories for Results ribbon primitives."""

from PyQt6.QtWidgets import QFrame

from opencae.ui.core.icon_factory import make_icon
from opencae.ui.primitives.buttons.button_results_ribbon_action import ButtonResultsRibbonAction
from opencae.ui.primitives.buttons.button_results_ribbon_toggle import ButtonResultsRibbonToggle


def ribbon_button(text, icon, checked=False, width=76):
    icon_value = make_icon(icon, 28)
    if checked is None:
        return ButtonResultsRibbonAction(text, icon=icon_value, width=width)
    return ButtonResultsRibbonToggle(
        text,
        icon=icon_value,
        checked=bool(checked),
        width=width,
    )


def action_button(action, width=76):
    return ButtonResultsRibbonAction(action=action, width=width)


def vertical_separator():
    # Kept as compatibility for the legacy Results-only separator geometry.
    line = QFrame()
    line.setFrameShape(QFrame.Shape.VLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    line.setFixedWidth(10)
    line.setContentsMargins(4, 8, 4, 8)
    return line
