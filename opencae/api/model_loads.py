"""Creates amplitude and load entities from the object-based public API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from opencae.model.entities import (
    Amplitude,
    ConcentratedLoad,
    CoordinateSystem,
    Instance,
    PressureLoad,
    Region,
)

if TYPE_CHECKING:
    from .model import Model


def create_amplitude(
    model: "Model",
    name: str,
    *,
    points: Iterable[tuple[float, float]],
    interpolation: str = "Linear",
    time_basis: str = "Step time",
) -> Amplitude:
    """Create and attach one reusable tabular load amplitude."""
    amplitude = Amplitude(
        name=name,
        points=list(points),
        interpolation=interpolation,
        time_basis=time_basis,
    )
    model.project.amplitudes.append(amplitude)
    model._refresh()
    return amplitude


def create_concentrated_load(
    model: "Model",
    name: str,
    *,
    target: Region,
    components: Iterable[float],
    coordinate_system: CoordinateSystem | None = None,
    amplitude: Amplitude | None = None,
    instance: Instance | None = None,
) -> ConcentratedLoad:
    """Create and attach a concentrated load using object relationships."""
    model._require_owned(target, Region)
    if coordinate_system is not None:
        model._require_owned(coordinate_system, CoordinateSystem)
    if amplitude is not None:
        model._require_owned(amplitude, Amplitude)

    values = [float(value) for value in components]
    if len(values) != 6:
        raise ValueError("A concentrated load requires six components")

    load = ConcentratedLoad(
        name=name,
        target=model.region_target(target, instance=instance),
        components=values,
    )
    load.coordinate_system = coordinate_system
    load.amplitude = amplitude

    # Attach only after validation so no partial load enters the project graph.
    model.project.loads.append(load)
    model._refresh()
    return load


def create_pressure_load(
    model: "Model",
    name: str,
    *,
    target: Region,
    pressure: float,
    amplitude: Amplitude | None = None,
    instance: Instance | None = None,
) -> PressureLoad:
    """Create and attach a pressure load using a Region object target."""
    model._require_owned(target, Region)
    if amplitude is not None:
        model._require_owned(amplitude, Amplitude)
    load = PressureLoad(
        name=name,
        target=model.region_target(target, instance=instance),
        pressure=float(pressure),
    )
    load.amplitude = amplitude
    model.project.loads.append(load)
    model._refresh()
    return load
