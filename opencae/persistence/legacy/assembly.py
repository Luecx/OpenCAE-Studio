from opencae.model.assembly import Assembly, Instance, create_constraint
from opencae.model.core import EntityRef
from opencae.model.selection import RegionProjection

from .part import legacy_csys, legacy_reference_point, legacy_region


def legacy_assembly(data):
    data = dict(data)
    collections = {key: data.pop(key, []) for key in (
        "instances", "node_sets", "element_sets", "surfaces",
        "coordinate_systems", "reference_points", "constraints",
    )}
    assembly = Assembly(**data)
    assembly.instances = [legacy_instance(item) for item in collections["instances"]]
    assembly.regions = [
        *(legacy_region(item, projection=RegionProjection.NODES) for item in collections["node_sets"]),
        *(legacy_region(item, projection=RegionProjection.ELEMENTS) for item in collections["element_sets"]),
        *(legacy_region(item, projection=RegionProjection.FACETS) for item in collections["surfaces"]),
    ]
    assembly.coordinate_systems = [legacy_csys(item) for item in collections["coordinate_systems"]]
    assembly.reference_points = [legacy_reference_point(item) for item in collections["reference_points"]]
    assembly.constraints = [legacy_constraint(item) for item in collections["constraints"]]
    return assembly


def legacy_instance(data):
    values = dict(data)
    name = values.pop("part_name", "")
    if name and "part_ref" not in values:
        values["part_ref"] = EntityRef(expected_type="Part", legacy_name=name)
    values["translation"] = tuple(values.get("translation", (0, 0, 0)))
    values["rotation"] = tuple(values.get("rotation", (0, 0, 0)))
    return Instance(**values)


def legacy_constraint(data):
    data = dict(data)
    return create_constraint(data.pop("constraint_type", "Constraint"), **data)
