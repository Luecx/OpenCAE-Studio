from __future__ import annotations

from ..command import command


def write_support(support, writer, context):
    target = _target(support.region_name, context)
    values = list(getattr(support, "components", ()) or ())
    if len(values) != 6:
        values = _legacy_support_values(support)
    command(writer, "SUPPORT", [(target, *values)], SUPPORT_COLLECTOR=support.name, ORIENTATION=_orientation(support.coordinate_system))


def write_load(load, writer, context):
    target = _target(load.region_name, context)
    orientation = _orientation(getattr(load, "coordinate_system", "Global"))
    kind = load.load_type
    if kind == "Concentrated Load":
        command(writer, "CLOAD", [(target, *_components(load, 6))], LOAD_COLLECTOR=load.name, ORIENTATION=orientation)
    elif kind == "Surface Traction":
        command(writer, "DLOAD", [(target, *_components(load, 3))], LOAD_COLLECTOR=load.name, ORIENTATION=orientation)
    elif kind == "Pressure":
        pressure = getattr(load, "pressure", getattr(load, "magnitude", 0.0))
        command(writer, "PLOAD", [(target, pressure)], LOAD_COLLECTOR=load.name)
    elif kind == "Volume Load":
        command(writer, "VLOAD", [(target, *_components(load, 3))], LOAD_COLLECTOR=load.name, ORIENTATION=orientation)
    elif kind == "Temperature":
        command(writer, "TLOAD", LOAD_COLLECTOR=load.name, TEMPERATUREFIELD=load.temperature_field, REFERENCETEMPERATURE=load.reference_temperature)
    elif kind == "Inertia Load":
        row = (target, *load.center, *load.center_acceleration, *load.angular_velocity, *load.angular_acceleration)
        command(writer, "INERTIALOAD", [row], LOAD_COLLECTOR=load.name, CONSIDER_POINT_MASSES=load.consider_point_masses)
    else:
        _legacy_load(load, writer, context)


def _legacy_load(load, writer, context):
    target = _target(load.region_name, context); orientation = _orientation(load.coordinate_system)
    if load.load_type in {"Force", "Moment"}:
        vector = [0.0] * 6; vector[_direction_index(load.direction, load.load_type == "Moment")] = load.magnitude
        command(writer, "CLOAD", [(target, *vector)], LOAD_COLLECTOR=load.name, ORIENTATION=orientation)
    elif load.load_type == "Pressure":
        command(writer, "PLOAD", [(target, load.magnitude)], LOAD_COLLECTOR=load.name)
    elif load.load_type in {"Gravity", "Body load"}:
        vector = [0.0] * 3; vector[_direction_index(load.direction) % 3] = load.magnitude
        command(writer, "VLOAD", [(target or "EALL", *vector)], LOAD_COLLECTOR=load.name, ORIENTATION=orientation)


def _components(load, size):
    values = list(getattr(load, "components", ()) or ())
    return (values + [0.0] * size)[:size]


def _legacy_support_values(support):
    if support.support_type == "Fixed": return [0.0] * 6
    values = support.metadata.get("components", [None] * 6)
    if support.support_type == "Symmetry": values = [0.0, None, None, None, None, None]
    return [float(value) if value not in (None, "", "NAN") else None for value in values]


def _target(name, context): return context.options.get("region_aliases", {}).get(name, name)
def _orientation(value): return None if value in (None, "", "Global") else value


def _direction_index(direction, moment=False):
    text = str(direction).lower(); base = 3 if moment else 0
    if "y" in text: return base + 1
    if "z" in text: return base + 2
    return base
