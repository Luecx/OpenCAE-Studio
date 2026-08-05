"""Defines comparison operators accepted by topology constraints."""

from enum import StrEnum


class ConstraintOperator(StrEnum):
    """Comparison operators stored by optimization constraints."""

    LESS_EQUAL = "<="
    GREATER_EQUAL = ">="
    EQUAL = "="
