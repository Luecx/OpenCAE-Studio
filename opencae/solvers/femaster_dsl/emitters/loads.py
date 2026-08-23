"""Writes FEMaster load and support collectors from current region definitions."""

from __future__ import annotations

from opencae.model.entities.loads import (
    BodyLoad,
    ConcentratedLoad,
    DistributedLoad,
    ForceLoad,
    GravityLoad,
    InertiaLoad,
    MomentLoad,
    PressureLoad,
    TemperatureLoad,
    VolumeLoad,
)
from opencae.model.selection import NodalLoadDistribution, RegionProjection

from ..command import command
from .region_materialization import materialize_region


def write_support(support, writer, context):
    """Write one support collector."""
    target = materialize_region(
        support.target,
        RegionProjection.NODES,
        writer,
        context,
        owner=support,
        proposed_name=f"__{support.name}_TARGET",
        cache_key=("support-target", support.id),
    ).name
    values = list(getattr(support, "components", ()) or ())
    if len(values) != 6:
        raise ValueError(
            f"Support '{support.name}' must define exactly six components"
        )
    command(
        writer,
        "SUPPORT",
        [(target, *values)],
        SUPPORT_COLLECTOR=context.solver_name(support, support.name),
        ORIENTATION=_orientation(support.coordinate_system_ref, context),
    )


def write_load(load, writer, context):
    """Dispatch one Load entity to its FEMaster representation."""
    collector = context.solver_name(load, load.name)
    orientation = _orientation(
        getattr(load, "coordinate_system_ref", None),
        context,
    )

    if isinstance(load, TemperatureLoad):
        _write_temperature(load, writer, context, collector)
        return

    if isinstance(load, (ConcentratedLoad, ForceLoad, MomentLoad)):
        materialized = materialize_region(
            load.target,
            RegionProjection.NODES,
            writer,
            context,
            owner=load,
            proposed_name=f"__{load.name}_TARGET",
            cache_key=("load-target", load.id),
        )
        components = _nodal_components(load)
        if (
            isinstance(load, ConcentratedLoad)
            and load.distribution == NodalLoadDistribution.TOTAL_UNIFORM
        ):
            components = [value / materialized.count for value in components]
        command(
            writer,
            "CLOAD",
            [(materialized.name, *components)],
            LOAD_COLLECTOR=collector,
            ORIENTATION=orientation,
        )
        return

    if isinstance(load, DistributedLoad):
        target = _materialize(load, RegionProjection.FACETS, writer, context)
        command(
            writer,
            "DLOAD",
            [(target, *_components(load, 3))],
            LOAD_COLLECTOR=collector,
            ORIENTATION=orientation,
        )
        return

    if isinstance(load, PressureLoad):
        target = _materialize(load, RegionProjection.FACETS, writer, context)
        command(
            writer,
            "PLOAD",
            [(target, getattr(load, "pressure", getattr(load, "magnitude", 0.0)))],
            LOAD_COLLECTOR=collector,
        )
        return

    if isinstance(load, (VolumeLoad, GravityLoad, BodyLoad)):
        target = _materialize(load, RegionProjection.ELEMENTS, writer, context)
        vector = _components(load, 3)
        if isinstance(load, (GravityLoad, BodyLoad)):
            vector = [0.0] * 3
            vector[_direction_index(load.direction)] = load.magnitude
        command(
            writer,
            "VLOAD",
            [(target, *vector)],
            LOAD_COLLECTOR=collector,
            ORIENTATION=orientation,
        )
        return

    if isinstance(load, InertiaLoad):
        target = _materialize(load, RegionProjection.ELEMENTS, writer, context)
        row = (
            target,
            *load.center,
            *load.center_acceleration,
            *load.angular_velocity,
            *load.angular_acceleration,
        )
        command(
            writer,
            "INERTIALOAD",
            [row],
            LOAD_COLLECTOR=collector,
            CONSIDER_POINT_MASSES=load.consider_point_masses,
        )
        return

    raise ValueError(f"Load class '{type(load).__name__}' has no FEMaster mapping")


def _materialize(load, projection, writer, context):
    return materialize_region(
        load.target,
        projection,
        writer,
        context,
        owner=load,
        proposed_name=f"__{load.name}_TARGET",
        cache_key=("load-target", load.id),
    ).name


def _write_temperature(load, writer, context, collector):
    field = context.resolve(load.temperature_field_ref)
    if field is None:
        raise ValueError(
            f"Temperature load '{load.name}' has no valid temperature field"
        )
    command(
        writer,
        "TLOAD",
        LOAD_COLLECTOR=collector,
        TEMPERATUREFIELD=context.solver_name(field, field.name),
        REFERENCETEMPERATURE=load.reference_temperature,
    )


def _nodal_components(load):
    if isinstance(load, ForceLoad):
        values = [0.0] * 6
        values[_direction_index(load.direction)] = load.magnitude
        return values
    if isinstance(load, MomentLoad):
        values = [0.0] * 6
        values[3 + _direction_index(load.direction)] = load.magnitude
        return values
    return _components(load, 6)


def _orientation(ref, context):
    if ref is None:
        return None
    entity = context.resolve(ref)
    if entity is None:
        raise ValueError("Referenced coordinate system no longer exists")
    return context.solver_name(entity, entity.name)


def _components(load, size):
    return (list(getattr(load, "components", ()) or ()) + [0.0] * size)[:size]


def _direction_index(direction):
    text = str(direction).lower()
    if "y" in text:
        return 1
    if "z" in text:
        return 2
    return 0
