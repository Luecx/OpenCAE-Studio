from opencae.model.assembly import Assembly, Instance, create_constraint

from .part import legacy_csys, legacy_reference_point, legacy_region


def legacy_assembly(data):
    collections = {key: data.pop(key, []) for key in (
        "instances", "node_sets", "element_sets", "surfaces",
        "coordinate_systems", "reference_points", "constraints",
    )}
    assembly = Assembly(**data)
    assembly.instances = [legacy_instance(item) for item in collections["instances"]]
    assembly.node_sets = [legacy_region(item) for item in collections["node_sets"]]
    assembly.element_sets = [legacy_region(item) for item in collections["element_sets"]]
    assembly.surfaces = [legacy_region(item) for item in collections["surfaces"]]
    assembly.coordinate_systems = [legacy_csys(item) for item in collections["coordinate_systems"]]
    assembly.reference_points = [legacy_reference_point(item) for item in collections["reference_points"]]
    assembly.constraints = [legacy_constraint(item) for item in collections["constraints"]]
    return assembly


def legacy_instance(data):
    return Instance(**{
        **data,
        "translation": tuple(data.get("translation", (0, 0, 0))),
        "rotation": tuple(data.get("rotation", (0, 0, 0))),
    })


def legacy_constraint(data):
    data = dict(data)
    return create_constraint(data.pop("constraint_type", "Constraint"), **data)
