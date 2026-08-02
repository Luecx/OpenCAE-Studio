from __future__ import annotations

from opencae.model.core import EntityTarget, MeshElementTarget, MeshNodeTarget
from ..command import command
from .target_resolution import entity_target_name


def write_support(support, writer, context):
    target = _target(support.target, writer, context, support)
    values = list(getattr(support, "components", ()) or ())
    if len(values) != 6:
        values = _legacy_support_values(support)
    command(
        writer,
        "SUPPORT",
        [(target, *values)],
        SUPPORT_COLLECTOR=context.solver_name(support, support.name),
        ORIENTATION=_orientation(support.coordinate_system_ref, context),
    )


def write_load(load, writer, context):
    target = _target(load.target, writer, context, load) if load.load_type != "Temperature" else None
    orientation = _orientation(getattr(load, "coordinate_system_ref", None), context)
    kind = load.load_type
    collector = context.solver_name(load, load.name)
    if kind == "Concentrated Load":
        command(writer, "CLOAD", [(target, *_components(load, 6))], LOAD_COLLECTOR=collector, ORIENTATION=orientation)
    elif kind == "Surface Traction":
        command(writer, "DLOAD", [(target, *_components(load, 3))], LOAD_COLLECTOR=collector, ORIENTATION=orientation)
    elif kind == "Pressure":
        command(writer, "PLOAD", [(target, getattr(load, "pressure", getattr(load, "magnitude", 0.0)))], LOAD_COLLECTOR=collector)
    elif kind == "Volume Load":
        command(writer, "VLOAD", [(target, *_components(load, 3))], LOAD_COLLECTOR=collector, ORIENTATION=orientation)
    elif kind == "Temperature":
        field = context.resolve(load.temperature_field_ref)
        if field is None:
            legacy = load.temperature_field_ref.legacy_name if load.temperature_field_ref else ""
            if not legacy:
                raise ValueError(f"Temperature load '{load.name}' has no valid temperature field")
            field_name = legacy
        else:
            field_name = context.solver_name(field, field.name)
        command(writer, "TLOAD", LOAD_COLLECTOR=collector, TEMPERATUREFIELD=field_name, REFERENCETEMPERATURE=load.reference_temperature)
    elif kind == "Inertia Load":
        row = (target, *load.center, *load.center_acceleration, *load.angular_velocity, *load.angular_acceleration)
        command(writer, "INERTIALOAD", [row], LOAD_COLLECTOR=collector, CONSIDER_POINT_MASSES=load.consider_point_masses)
    else:
        _legacy_load(load, writer, context, target, collector, orientation)


def _legacy_load(load, writer, context, target, collector, orientation):
    if load.load_type in {"Force", "Moment"}:
        vector = [0.0] * 6
        vector[_direction_index(load.direction, load.load_type == "Moment")] = load.magnitude
        command(writer, "CLOAD", [(target, *vector)], LOAD_COLLECTOR=collector, ORIENTATION=orientation)
    elif load.load_type == "Pressure":
        command(writer, "PLOAD", [(target, load.magnitude)], LOAD_COLLECTOR=collector)
    elif load.load_type in {"Gravity", "Body load"}:
        vector = [0.0] * 3
        vector[_direction_index(load.direction) % 3] = load.magnitude
        command(writer, "VLOAD", [(target or "EALL", *vector)], LOAD_COLLECTOR=collector, ORIENTATION=orientation)


def _target(target, writer, context, owner):
    if isinstance(target, EntityTarget):
        entity = context.resolve(target.ref)
        if entity is None:
            legacy = target.ref.legacy_name
            if legacy:
                return context.options.get("region_aliases", {}).get(legacy, legacy)
            raise ValueError(f"Target of '{owner.name}' no longer exists")
        return entity_target_name(entity, target.kind.value, writer, context)
    if isinstance(target, MeshNodeTarget):
        return _single_member_set("NSET", target.owner_ref, target.node_id, writer, context, owner)
    if isinstance(target, MeshElementTarget):
        return _single_member_set("ELSET", target.owner_ref, target.element_id, writer, context, owner)
    raise ValueError(f"{type(owner).__name__} '{owner.name}' has no valid target")


def _single_member_set(command_name, owner_ref, local_id, writer, context, owner):
    mapping_name = "instance_node_maps" if command_name == "NSET" else "instance_element_maps"
    mapping = context.options.get(mapping_name, {}).get(owner_ref.entity_id, {})
    exported = mapping.get(int(local_id), int(local_id))
    name = context.names.register(("single-target", owner.id, command_name), f"__{owner.name}_TARGET")
    command(writer, command_name, [(exported,)], **{command_name: name})
    return name


def _orientation(ref, context):
    if ref is None:
        return None
    entity = context.resolve(ref)
    if entity is None:
        raise ValueError("Referenced coordinate system no longer exists")
    return context.solver_name(entity, entity.name)


def _components(load, size):
    return (list(getattr(load, "components", ()) or ()) + [0.0] * size)[:size]


def _legacy_support_values(support):
    if support.support_type == "Fixed":
        return [0.0] * 6
    values = support.metadata.get("components", [None] * 6)
    if support.support_type == "Symmetry":
        values = [0.0, None, None, None, None, None]
    return [float(value) if value not in (None, "", "NAN") else None for value in values]


def _direction_index(direction, moment=False):
    text = str(direction).lower()
    base = 3 if moment else 0
    if "y" in text:
        return base + 1
    if "z" in text:
        return base + 2
    return base
