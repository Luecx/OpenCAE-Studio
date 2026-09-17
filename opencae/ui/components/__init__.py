"""Reusable UI compositions built exclusively from canonical primitives."""

from .collapsed_action_group import CollapsedActionGroupButton
from .automatic_manual_value_editor import AutomaticManualValueEditor
from .compact_region_selector import CompactRegionSelector
from .components import ComponentsWidget
from .controls import (
    ControlPickReference,
    ControlReferenceSelector,
    ControlXYZPicker,
)
from .entity_selector_bar import EntitySelectorBar
from .field_row import FieldRow
from .field_stack import FieldStack
from .form_field import FormField
from .matrix_editor import MatrixEditor
from .monospace_output_view import MonospaceOutputView
from .point_selection import PointSelectionWidget
from .region_selection import RegionSelectionWidget
from .amplitude_curve import AmplitudeCurvePreview

__all__ = [
    "CollapsedActionGroupButton",
    "AmplitudeCurvePreview",
    "AutomaticManualValueEditor",
    "CompactRegionSelector",
    "ComponentsWidget",
    "ControlPickReference",
    "ControlReferenceSelector",
    "ControlXYZPicker",
    "EntitySelectorBar",
    "FieldRow",
    "FieldStack",
    "FormField",
    "MatrixEditor",
    "MonospaceOutputView",
    "PointSelectionWidget",
    "RegionSelectionWidget",
]
