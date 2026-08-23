"""Creates load entities from object-based public API targets."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from opencae.model.entities import (
    ConcentratedLoad,
    CoordinateSystem,
    Instance,
    PressureLoad,
    Region,
)

if TYPE_CHECKING:
    from .model import Model


def create_concentrated_load(
    model: "Model",
    name: str,
    *,
    target: Region,
    components: Iterable[float],
    coordinate_system: CoordinateSystem | None = None,
    instance: Instance | None = None,
) -> ConcentratedLoad:
    """Create and attach a concentrated load using object relationships."""
    model._require_owned(target, Region)
    if coordinate_system is not None:
        model._require_owned(coordinate_system, CoordinateSystem)

    values = [float(value) for value in components]
    if len(values) != 6:
        raise ValueError("A concentrated load requires six components")

    load = ConcentratedLoad(
        name=name,
        target=model.region_target(target, instance=instance),
        components=values,
    )
    load.coordinate_system = coordinate_system

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
    instance: Instance | None = None,
) -> PressureLoad:
    """Create and attach a pressure load using a Region object target."""
    model._require_owned(target, Region)
    load = PressureLoad(
        name=name,
        target=model.region_target(target, instance=instance),
        pressure=float(pressure),
    )
    model.project.loads.append(load)
    model._refresh()
    return load
