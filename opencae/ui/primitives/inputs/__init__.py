"""Canonical low-level input controls used by reusable OpenCAE composites."""

# Canonical structurally named primitives -----------------------------------
from .input_form_integer import InputFormInteger
from .input_form_multiline import InputFormMultiline
from .input_form_number import InputFormNumber
from .input_form_text import InputFormText
from .input_matrix_number import InputMatrixNumber
from .input_search import InputSearch
from .input_time_manager_speed import InputTimeManagerSpeed

# Transitional names retained while callers are migrated --------------------
from .boolean_input import BooleanInput
from .choice_input import ChoiceInput
from .integer_input import IntegerInput
from .number_input import NumberInput
from .text_input import TextInput

__all__ = [
    "InputFormInteger",
    "InputFormMultiline",
    "InputFormNumber",
    "InputFormText",
    "InputMatrixNumber",
    "InputSearch",
    "InputTimeManagerSpeed",
    "BooleanInput",
    "ChoiceInput",
    "IntegerInput",
    "NumberInput",
    "TextInput",
]
