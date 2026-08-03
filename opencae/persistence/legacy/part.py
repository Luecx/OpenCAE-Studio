from typing import Any

from opencae.model.geometry import (
    GeometryFeature, GeometrySettings, ImportedStepFeature, PartitionEdgeFeature,
    PartitionFaceFeature, PartitionPlaneFeature,
)
from opencae.model.core import EntityRef
from opencae.model.part import Part
from opencae.model.regions import CoordinateSystem, Orientation, ReferencePoint, SectionAssignment, create_region
from opencae.model.selection import RegionProjection, definition_from_local_labels

from .mesh import legacy_mesh


def legacy_part(data: dict[str, Any]) -> Part:
    geometry = data.pop("geometry", [])
    mesh = data.pop("mesh", {})
    settings = GeometrySettings(**data.pop("geometry_settings", {}))
    collections = {key: data.pop(key, []) for key in (
        "node_sets", "element_sets", "surfaces", "coordinate_systems",
        "reference_points", "orientations", "section_assignments",
    )}
    part = Part(**data, geometry_settings=settings)
    part.geometry = [legacy_feature(item, part) for item in geometry]
    part.mesh = legacy_mesh(mesh)
    part.regions = [
        *(legacy_region(item, part, RegionProjection.NODES) for item in collections["node_sets"]),
        *(legacy_region(item, part, RegionProjection.ELEMENTS) for item in collections["element_sets"]),
        *(legacy_region(item, part, RegionProjection.FACETS) for item in collections["surfaces"]),
    ]
    part.coordinate_systems = [legacy_csys(item) for item in collections["coordinate_systems"]]
    part.reference_points = [legacy_reference_point(item) for item in collections["reference_points"]]
    part.orientations = [_legacy_orientation(item) for item in collections["orientations"]]
    part.section_assignments = [_legacy_assignment(item) for item in collections["section_assignments"]]
    return part


def legacy_feature(data, owner):
    data = dict(data)
    kind = data.pop("feature_type", "Geometry Feature")
    references = data.pop("references", ())
    parameters = dict(data.pop("parameters", {}) or {})
    target = definition_from_local_labels(owner, references)
    if kind.startswith("Imported"):
        return ImportedStepFeature(target=target, source_file=str(parameters.pop("file", "")), parameters=parameters, **data)
    if kind == "Partition by Plane":
        return PartitionPlaneFeature(
            target=target, origin=parameters.pop("origin", (0, 0, 0)),
            normal=parameters.pop("normal", (1, 0, 0)), parameters=parameters, **data,
        )
    if kind == "Partition Face":
        return PartitionFaceFeature(target=target, points=tuple(parameters.pop("points", ())), parameters=parameters, **data)
    if kind == "Partition Edge":
        split_target = definition_from_local_labels(owner, parameters.pop("vertices", ()))
        return PartitionEdgeFeature(
            target=target, split_target=split_target, method=parameters.pop("method", "Parameter"),
            fraction=parameters.pop("fraction", 0.5), parameters=parameters, **data,
        )
    return GeometryFeature(feature_type=kind, target=target, parameters=parameters, **data)


def legacy_region(data, owner=None, projection=None):
    from opencae.model.selection import RegionDefinition, RegionSelectionItem, UnresolvedOperand

    data = dict(data)
    members = data.pop("members", ())
    if owner is not None:
        data["definition"] = definition_from_local_labels(owner, members)
    elif members:
        data["definition"] = RegionDefinition(tuple(
            RegionSelectionItem(UnresolvedOperand(str(member), "legacy_assembly_member"), display_label=str(member))
            for member in members
        ))
    region_type = data.pop("region_type", "Region")
    data.setdefault("preferred_projection", projection or RegionProjection.coerce(region_type))
    return create_region("Region", **data)


def legacy_csys(data):
    return CoordinateSystem(**{
        **data,
        "origin": tuple(data.get("origin", (0, 0, 0))),
        "axis_1": tuple(data.get("axis_1", (1, 0, 0))),
        "axis_2": tuple(data.get("axis_2", (0, 1, 0))),
    })


def legacy_reference_point(data):
    return ReferencePoint(**{**data, "position": tuple(data.get("position", (0, 0, 0)))})


def _legacy_orientation(data):
    values = dict(data)
    region = values.pop("region_name", "")
    csys = values.pop("coordinate_system_name", "")
    if region and "region_ref" not in values:
        values["region_ref"] = EntityRef(expected_type="Region", legacy_name=region)
    if csys and csys != "Global" and "coordinate_system_ref" not in values:
        values["coordinate_system_ref"] = EntityRef(expected_type="CoordinateSystem", legacy_name=csys)
    return Orientation(**values)


def _legacy_assignment(data):
    values = dict(data)
    section = values.pop("section_name", "")
    region = values.pop("region_name", "")
    orientation = values.pop("orientation_name", "")
    if section and "section_ref" not in values:
        values["section_ref"] = EntityRef(expected_type="Section", legacy_name=section)
    if region and "region_ref" not in values:
        values["region_ref"] = EntityRef(expected_type="Region", legacy_name=region)
    if orientation and orientation != "Global" and "orientation_ref" not in values:
        values["orientation_ref"] = EntityRef(expected_type="Orientation", legacy_name=orientation)
    return SectionAssignment(**values)
