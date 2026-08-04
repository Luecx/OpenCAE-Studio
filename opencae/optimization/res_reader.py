"""Compatibility exports for split FEMaster native result modules."""

from .res_field import ResField
from .res_field_reader import ResFieldReader
from .res_format_error import ResFormatError
from .res_values import dense_values

__all__ = [
    "ResField",
    "ResFieldReader",
    "ResFormatError",
    "dense_values",
]
