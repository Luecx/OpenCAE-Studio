"""Defines the canonical finite set of supported analysis procedures."""

from enum import StrEnum


class StepType(StrEnum):
    """Identify one solver-neutral analysis procedure throughout the application."""

    LINEAR_STATIC = "Linear Static"
    LINEAR_STATIC_TOPOLOGY = "Linear Static Topology"
    NONLINEAR_STATIC = "Nonlinear Static"
    EIGENFREQUENCY = "Eigenfrequency"
    LINEAR_BUCKLING = "Linear Buckling"
    TRANSIENT = "Transient"

    @classmethod
    def coerce(cls, value) -> "StepType":
        """Normalize API and persisted values to a canonical procedure member."""
        if isinstance(value, cls):
            return value
        text = str(value or cls.LINEAR_STATIC.value).strip()
        aliases = {
            "linear transient": cls.TRANSIENT,
        }
        alias = aliases.get(text.casefold())
        if alias is not None:
            return alias
        for step_type in cls:
            if step_type.value.casefold() == text.casefold():
                return step_type
        raise ValueError(f"Unknown analysis step type: {value!r}")
