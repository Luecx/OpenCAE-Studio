from opencae.model.core import EntityRef, TargetKind, entity_target
from opencae.model.loads import create_load, create_support
from opencae.model.resources import create_profile, create_section


def legacy_load(data):
    values = dict(data)
    load_type = values.pop("load_type", "Load")
    _migrate_target(values, _load_target_kind(load_type))
    _migrate_coordinate_system(values)
    field_name = values.pop("temperature_field", "")
    if field_name and "temperature_field_ref" not in values:
        values["temperature_field_ref"] = EntityRef(expected_type="FieldDefinition", legacy_name=field_name)
    values.pop("step_name", None)
    return create_load(load_type, **values)


def legacy_support(data):
    values = dict(data)
    support_type = values.pop("support_type", "Support")
    _migrate_target(values, TargetKind.NODE_SET)
    _migrate_coordinate_system(values)
    values.pop("step_name", None)
    return create_support(support_type, **values)


def legacy_profile(data):
    data = dict(data)
    return create_profile(data.pop("profile_type", "General"), **data)


def legacy_section(data):
    values = dict(data)
    section_type = values.pop("section_type", "Section")
    material = values.pop("material_name", "")
    profile = values.pop("profile_name", "")
    if material and "material_ref" not in values:
        values["material_ref"] = EntityRef(expected_type="Material", legacy_name=material)
    if profile and "profile_ref" not in values:
        values["profile_ref"] = EntityRef(expected_type="Profile", legacy_name=profile)
    return create_section(section_type, **values)


def _migrate_target(values, kind):
    name = values.pop("region_name", "")
    if name and "target" not in values:
        values["target"] = entity_target(EntityRef(expected_type=kind.value.replace(" ", ""), legacy_name=name), kind)


def _migrate_coordinate_system(values):
    name = values.pop("coordinate_system", "")
    if name and name != "Global" and "coordinate_system_ref" not in values:
        values["coordinate_system_ref"] = EntityRef(expected_type="CoordinateSystem", legacy_name=name)


def _load_target_kind(load_type):
    if load_type in {"Pressure", "Surface Traction"}:
        return TargetKind.SURFACE
    if load_type in {"Volume Load", "Inertia Load", "Gravity", "Body load"}:
        return TargetKind.ELEMENT_SET
    return TargetKind.NODE_SET
