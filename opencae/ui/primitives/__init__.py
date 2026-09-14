"""Canonical low-level OpenCAE UI primitives.

Primitives are flat concrete widgets named by visual context and behavior.
Higher-level composites, dialogs, ribbons, and workspaces compose these classes
instead of inheriting from a shared widget hierarchy.
"""

from .buttons import *
from .checks import CheckForm
from .inputs import (
    InputFormInteger,
    InputFormMultiline,
    InputFormNumber,
    InputFormText,
    InputMatrixNumber,
    InputSearch,
    InputTimeManagerSpeed,
)
from .labels import (
    LabelBody,
    LabelForm,
    LabelGroup,
    LabelMatrixHeader,
    LabelMuted,
    LabelRibbonGroup,
    LabelSection,
    LabelStatus,
    LabelTimeManagerHeading,
    LabelTitle,
)
from .radios import RadioForm
from .selects import SelectForm
from .sliders import SliderHorizontal

__all__ = [name for name in globals() if name.startswith(("Button", "Input", "Label"))]
__all__ += [
    "CheckForm",
    "RadioForm",
    "SelectForm",
    "SliderHorizontal",
    "ribbon_button_for_action",
]
