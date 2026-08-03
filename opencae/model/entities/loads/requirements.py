from __future__ import annotations

from opencae.model.selection import (
    RegionProjection,
    RegionRequirement,
    SelectableKind,
    SelectionPolicy,
)


def load_region_projection(value) -> RegionProjection | None:
    """Return the solver projection required by a load class or UI type label."""
    from .base import Load
    from .body import BodyLoad
    from .concentrated import ConcentratedLoad
    from .distributed import DistributedLoad
    from .force import ForceLoad
    from .gravity import GravityLoad
    from .inertia import InertiaLoad
    from .moment import MomentLoad
    from .pressure import PressureLoad
    from .temperature import TemperatureLoad
    from .volume import VolumeLoad

    if isinstance(value, type): cls = value
    elif isinstance(value, Load): cls = type(value)
    else:
        labels = {
            "Concentrated Load": ConcentratedLoad,
            "Force": ForceLoad,
            "Moment": MomentLoad,
            "Surface Traction": DistributedLoad,
            "Pressure": PressureLoad,
            "Volume Load": VolumeLoad,
            "Gravity": GravityLoad,
            "Body load": BodyLoad,
            "Inertia Load": InertiaLoad,
            "Temperature": TemperatureLoad,
        }
        cls = labels.get(str(value), Load)
    if issubclass(cls, TemperatureLoad): return None
    if issubclass(cls, (DistributedLoad, PressureLoad)): return RegionProjection.FACETS
    if issubclass(cls, (VolumeLoad, GravityLoad, BodyLoad, InertiaLoad)): return RegionProjection.ELEMENTS
    return RegionProjection.NODES


def load_region_requirement(value) -> RegionRequirement | None:
    projection = load_region_projection(value)
    if projection is None: return None
    dimensions = (2,) if projection == RegionProjection.FACETS else (1, 2, 3) if projection == RegionProjection.ELEMENTS else (0, 1, 2, 3)
    return RegionRequirement(projection, dimensions, 1)


def load_selection_policy(value) -> SelectionPolicy | None:
    requirement = load_region_requirement(value)
    if requirement is None: return None
    if requirement.projection == RegionProjection.FACETS:
        kinds = {SelectableKind.GEOMETRY_FACE, SelectableKind.MESH_ELEMENT, SelectableKind.MESH_FACET}
    elif requirement.projection == RegionProjection.ELEMENTS:
        kinds = {
            SelectableKind.GEOMETRY_EDGE, SelectableKind.GEOMETRY_FACE,
            SelectableKind.GEOMETRY_CELL, SelectableKind.MESH_ELEMENT,
        }
    else:
        kinds = {
            SelectableKind.GEOMETRY_VERTEX, SelectableKind.GEOMETRY_EDGE,
            SelectableKind.GEOMETRY_FACE, SelectableKind.GEOMETRY_CELL,
            SelectableKind.MESH_NODE, SelectableKind.MESH_ELEMENT,
            SelectableKind.REFERENCE_POINT,
        }
    return SelectionPolicy.create(kinds, multiple=True, requirement=requirement)
