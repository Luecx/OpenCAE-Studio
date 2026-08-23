"""Creates assembly occurrences and coordinate systems for the Model facade."""

from __future__ import annotations

from typing import TYPE_CHECKING

from opencae.model.entities import Assembly, CoordinateSystem, Instance, Part

if TYPE_CHECKING:
    from .model import Model


def create_instance(
    model: "Model",
    part: Part,
    *,
    name: str | None = None,
    translation=(0.0, 0.0, 0.0),
    rotation=(0.0, 0.0, 0.0),
) -> Instance:
    """Create an assembly Instance that references a Part object."""
    model._require_owned(part, Part)
    instance = Instance(
        name=name or f"{part.name}-1",
        translation=tuple(float(value) for value in translation),
        rotation=tuple(float(value) for value in rotation),
    )

    # The persisted field remains ``part_ref`` while the authoring boundary uses
    # the actual Part object.
    instance.part = part
    model.project.assembly.instances.append(instance)
    model._refresh()
    return instance


def create_coordinate_system(
    model: "Model",
    owner: Part | Assembly,
    *,
    name: str,
    origin=(0.0, 0.0, 0.0),
    axis_1=(1.0, 0.0, 0.0),
    axis_2=(0.0, 1.0, 0.0),
    system_type: str = "Cartesian",
) -> CoordinateSystem:
    """Create a coordinate system in a validated part or assembly scope."""
    model._require_owned(owner, (Part, Assembly))
    scope = "Part" if isinstance(owner, Part) else "Assembly"
    coordinate_system = CoordinateSystem(
        name=name,
        system_type=system_type,
        origin=tuple(float(value) for value in origin),
        axis_1=tuple(float(value) for value in axis_1),
        axis_2=tuple(float(value) for value in axis_2),
        scope=scope,
    )
    owner.coordinate_systems.append(coordinate_system)
    model._refresh()
    return coordinate_system
