"""Persistent scalar amplitude definitions and portable function sampling."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import asin, cos, exp, isfinite, pi, sin

from ...core import Entity, register_model_type


INTERPOLATIONS = ("Linear", "Step", "Smooth Step")
TIME_BASES = ("Step time", "Total time")
FUNCTION_TYPES = (
    "Constant",
    "Ramp",
    "Sine",
    "Cosine",
    "Triangle",
    "Square",
    "Exponential Decay",
    "Smooth Step",
)
FUNCTION_DEFAULTS = {
    "Constant": {"value": 1.0},
    "Ramp": {"start_value": 0.0, "end_value": 1.0},
    "Sine": {"amplitude": 1.0, "frequency": 1.0, "phase": 0.0, "offset": 0.0},
    "Cosine": {"amplitude": 1.0, "frequency": 1.0, "phase": 0.0, "offset": 0.0},
    "Triangle": {"amplitude": 1.0, "frequency": 1.0, "phase": 0.0, "offset": 0.0},
    "Square": {"amplitude": 1.0, "frequency": 1.0, "phase": 0.0, "offset": 0.0},
    "Exponential Decay": {"amplitude": 1.0, "decay": 1.0, "offset": 0.0},
    "Smooth Step": {"start_value": 0.0, "end_value": 1.0},
}


@register_model_type("amplitude")
@dataclass
class Amplitude(Entity):
    """Dimensionless time/value multiplier referenced by one or more loads.

    ``points`` are the authoritative persisted representation. Function-based
    definitions are sampled into these points on creation/edit so exporters and
    solvers only need to understand tabular data. The source fields are retained
    solely so the function editor can be reopened with the original parameters.
    """

    points: list[tuple[float, float]] = field(
        default_factory=lambda: [(0.0, 0.0), (1.0, 1.0)]
    )
    interpolation: str = "Linear"
    time_basis: str = "Step time"
    source_mode: str = "Tabular"
    function_type: str = "Ramp"
    function_parameters: dict[str, float] = field(default_factory=dict)
    sample_start: float = 0.0
    sample_end: float = 1.0
    sample_intervals: int = 100

    def __post_init__(self) -> None:
        self.points = _normalized_points(self.points)
        if self.interpolation not in INTERPOLATIONS:
            raise ValueError(f"Unsupported amplitude interpolation: {self.interpolation}")
        if self.time_basis not in TIME_BASES:
            raise ValueError(f"Unsupported amplitude time basis: {self.time_basis}")
        if self.source_mode not in {"Tabular", "Function"}:
            raise ValueError(f"Unsupported amplitude source mode: {self.source_mode}")
        if self.function_type not in FUNCTION_TYPES:
            raise ValueError(f"Unsupported amplitude function: {self.function_type}")
        self.function_parameters = {
            str(key): float(value)
            for key, value in (self.function_parameters or {}).items()
        }
        self.sample_start = float(self.sample_start)
        self.sample_end = float(self.sample_end)
        self.sample_intervals = int(self.sample_intervals)
        if self.sample_intervals < 1:
            raise ValueError("Amplitude sample intervals must be at least one")

    def preview_points(self, samples_per_segment: int = 20) -> list[tuple[float, float]]:
        """Return a polyline representation suitable for UI plotting."""
        return preview_points(
            self.points,
            self.interpolation,
            samples_per_segment=samples_per_segment,
        )

    def linearized_points(self, samples_per_segment: int = 20) -> list[tuple[float, float]]:
        """Return a linear-only point table for formats without native interpolation.

        Step interpolation is intentionally not linearized here because FEMaster
        supports it directly and an exact mathematical jump cannot be represented
        by a finite strictly-increasing linear table. Callers that require a purely
        linear format should either support a step keyword or reject that case.
        """
        if self.interpolation == "Smooth Step":
            return preview_points(
                self.points,
                self.interpolation,
                samples_per_segment=samples_per_segment,
            )
        return list(self.points)


def sample_function(
    function_type: str,
    parameters: dict[str, float] | None,
    start: float,
    end: float,
    intervals: int,
) -> list[tuple[float, float]]:
    """Bake one analytical preset into a linearly interpolated point table."""
    if function_type not in FUNCTION_TYPES:
        raise ValueError(f"Unsupported amplitude function: {function_type}")
    start = float(start)
    end = float(end)
    intervals = int(intervals)
    if not (isfinite(start) and isfinite(end)):
        raise ValueError("Amplitude sampling bounds must be finite")
    if end <= start:
        raise ValueError("Amplitude sampling end must be greater than start")
    if intervals < 1:
        raise ValueError("Amplitude sample intervals must be at least one")
    if intervals > 10000:
        raise ValueError("Amplitude sample intervals must not exceed 10000")

    values = dict(FUNCTION_DEFAULTS[function_type])
    values.update(parameters or {})
    values = {key: float(value) for key, value in values.items()}
    points = []
    duration = end - start
    for index in range(intervals + 1):
        fraction = index / intervals
        time = start + duration * fraction
        points.append((time, _function_value(function_type, values, time, start, end)))
    return _normalized_points(points)


def preview_points(
    points,
    interpolation: str,
    *,
    samples_per_segment: int = 20,
) -> list[tuple[float, float]]:
    """Convert tabular knots into a plot polyline for the selected interpolation."""
    values = _normalized_points(points)
    if interpolation == "Linear":
        return values
    if interpolation == "Step":
        result = [values[0]]
        for (_x0, y0), (x1, y1) in zip(values, values[1:]):
            result.append((x1, y0))
            result.append((x1, y1))
        return result
    if interpolation == "Smooth Step":
        count = max(2, int(samples_per_segment))
        result = [values[0]]
        for (x0, y0), (x1, y1) in zip(values, values[1:]):
            for index in range(1, count + 1):
                fraction = index / count
                smooth = fraction * fraction * (3.0 - 2.0 * fraction)
                result.append((x0 + (x1 - x0) * fraction, y0 + (y1 - y0) * smooth))
        return result
    raise ValueError(f"Unsupported amplitude interpolation: {interpolation}")


def _normalized_points(points) -> list[tuple[float, float]]:
    values = [(float(x), float(y)) for x, y in (points or ())]
    if len(values) < 2:
        raise ValueError("An amplitude requires at least two time/value points")
    previous = None
    for x, y in values:
        if not (isfinite(x) and isfinite(y)):
            raise ValueError("Amplitude points must contain finite numbers")
        if previous is not None and x <= previous:
            raise ValueError("Amplitude times must be strictly increasing")
        previous = x
    return values


def _function_value(function_type, values, time, start, end) -> float:
    duration = end - start
    phase = values.get("phase", 0.0) * pi / 180.0
    omega_time = 2.0 * pi * values.get("frequency", 1.0) * (time - start) + phase
    amplitude = values.get("amplitude", 1.0)
    offset = values.get("offset", 0.0)

    if function_type == "Constant":
        return values["value"]
    if function_type == "Ramp":
        fraction = (time - start) / duration
        return values["start_value"] + (values["end_value"] - values["start_value"]) * fraction
    if function_type == "Sine":
        return offset + amplitude * sin(omega_time)
    if function_type == "Cosine":
        return offset + amplitude * cos(omega_time)
    if function_type == "Triangle":
        return offset + amplitude * (2.0 / pi) * asin(sin(omega_time))
    if function_type == "Square":
        return offset + amplitude * (1.0 if sin(omega_time) >= 0.0 else -1.0)
    if function_type == "Exponential Decay":
        return offset + amplitude * exp(-values.get("decay", 1.0) * (time - start))
    if function_type == "Smooth Step":
        fraction = max(0.0, min(1.0, (time - start) / duration))
        smooth = fraction * fraction * (3.0 - 2.0 * fraction)
        return values["start_value"] + (values["end_value"] - values["start_value"]) * smooth
    raise ValueError(f"Unsupported amplitude function: {function_type}")
