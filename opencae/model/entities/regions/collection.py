from __future__ import annotations

from collections.abc import Iterable

from opencae.model.selection import RegionProjection


def regions_with_projection(regions: Iterable, projection: RegionProjection | str | None):
    """Return regions matching one preferred solver projection.

    The returned list is a UI/read-only grouping. Persistent ownership always
    remains the owner's single ``regions`` collection.
    """

    expected = RegionProjection.coerce(projection)
    return [region for region in regions if region.preferred_projection == expected]
