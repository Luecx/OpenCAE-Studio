"""Curated public surface for reusable OpenCAE UI construction templates."""

from .button_role import ButtonRole
from .button_spec import ButtonSpec
from .control_metrics import (
    COMBO_POPUP_EXTRA_HEIGHT,
    COMBO_POPUP_ROW_HEIGHT,
    FIELD_LABEL_SPACING,
    INLINE_ACTION_SIZE,
    PRIMARY_CONTROL_HEIGHT,
    apply_inline_action_size,
    apply_primary_control_height,
)
from .dialogs import (
    DialogScaffold,
    apply_close_buttons,
    dialog_buttons,
    scaffold_dialog,
)
from .field_block import field_block
from .field_label import FieldLabel
from .field_row import field_row
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
from .numeric_unit_input import NumericUnitInput
from .primitives import (
    action_button,
    button,
    label,
    ribbon_label,
    wrapped_ribbon_text,
)
from .read_only_value import ReadOnlyValue
from .section_heading import SectionHeading
from .tables import read_only_table
from .vertical_separator import VerticalSeparator

__all__ = [
    "ButtonRole",
    "ButtonSpec",
    "LabelRole",
    "LabelSpec",
    "DialogScaffold",
    "FieldLabel",
    "NumericUnitInput",
    "ReadOnlyValue",
    "SectionHeading",
    "VerticalSeparator",
    "button",
    "label",
    "action_button",
    "action_group_button",
    "ribbon_label",
    "wrapped_ribbon_text",
    "form_layout",
    "field_block",
    "field_row",
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
    "PRIMARY_CONTROL_HEIGHT",
    "INLINE_ACTION_SIZE",
    "COMBO_POPUP_ROW_HEIGHT",
    "COMBO_POPUP_EXTRA_HEIGHT",
    "FIELD_LABEL_SPACING",
    "apply_primary_control_height",
    "apply_inline_action_size",
]
