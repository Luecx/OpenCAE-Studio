"""Compatibility factories for Results ribbon primitives."""

from opencae.ui.core.icon_factory import make_icon
from opencae.ui.primitives.buttons.button_results_ribbon_action import ButtonResultsRibbonAction
from opencae.ui.primitives.buttons.button_results_ribbon_toggle import ButtonResultsRibbonToggle
from opencae.ui.primitives.separators import SeparatorResultsRibbon


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
    return SeparatorResultsRibbon()
