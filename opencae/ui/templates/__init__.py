"""Curated public surface for reusable OpenCAE UI construction templates."""

from .button_role import ButtonRole
from .button_spec import ButtonSpec
from .dialogs import (
    DialogScaffold,
    apply_close_buttons,
    dialog_buttons,
    scaffold_dialog,
)
from .label_role import LabelRole
from .label_spec import LabelSpec
from .layouts import (
    CONTROL_GROUP_SPACING,
    DIALOG_MARGINS,
    DIALOG_SPACING,
    FORM_HORIZONTAL_SPACING,
    FORM_VERTICAL_SPACING,
    clear_layout,
    dialog_layout,
    form_layout,
    horizontal_group,
    vertical_group,
)
from .menus import action_group_button
from .primitives import (
    action_button,
    button,
    label,
    ribbon_label,
    wrapped_ribbon_text,
)
from .tables import read_only_table

__all__ = [
    "ButtonRole",
    "ButtonSpec",
    "LabelRole",
    "LabelSpec",
    "DialogScaffold",
    "button",
    "label",
    "action_button",
    "action_group_button",
    "ribbon_label",
    "wrapped_ribbon_text",
    "form_layout",
    "dialog_layout",
    "horizontal_group",
    "vertical_group",
    "clear_layout",
    "scaffold_dialog",
    "dialog_buttons",
    "apply_close_buttons",
    "read_only_table",
    "DIALOG_MARGINS",
    "DIALOG_SPACING",
    "FORM_HORIZONTAL_SPACING",
    "FORM_VERTICAL_SPACING",
    "CONTROL_GROUP_SPACING",
]
