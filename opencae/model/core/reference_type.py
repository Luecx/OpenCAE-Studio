"""Checks declared EntityRef type contracts against runtime model entities."""

from __future__ import annotations


def matches_reference_type(entity, expected_type: str) -> bool:
    """Return whether ``entity`` satisfies one persisted reference type name.

    EntityRef stores a small string contract so persistence remains decoupled
    from Python class objects. Normal inheritance is matched through the MRO;
    Region family aliases additionally enforce the region projection.
    """
    if not expected_type:
        return True

    expected = _normalized(expected_type)
    names = {_normalized(cls.__name__) for cls in type(entity).mro()}
    if expected in names:
        return True

    if expected not in {"region", "nodeset", "elementset", "surface"}:
        return False

    from opencae.model.entities.regions import Region
    from opencae.model.selection import RegionProjection

    if not isinstance(entity, Region):
        return False
    if expected == "region":
        return True

    projection = RegionProjection.coerce(entity.preferred_projection)
    required = {
        "nodeset": RegionProjection.NODES,
        "elementset": RegionProjection.ELEMENTS,
        "surface": RegionProjection.FACETS,
    }
    return projection == required[expected]


def expected_type_label(expected_type: str) -> str:
    """Return a stable human-readable label for one reference type contract."""
    return expected_type or "Entity"


def _normalized(value: str) -> str:
    """Normalize class-like reference type labels for comparison."""
    return str(value or "").replace(" ", "").replace("_", "").casefold()
