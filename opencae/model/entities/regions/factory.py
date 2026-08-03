from opencae.model.selection import RegionProjection
from .region import Region


def create_region(region_type: str = "Region", **kwargs) -> Region:
    """Create the unified runtime Region type.

    ``region_type`` is accepted only as an import/migration compatibility hint.
    New objects are never represented by separate NodeSet/ElementSet/Surface
    runtime classes.
    """

    kwargs.setdefault("preferred_projection", RegionProjection.coerce(region_type))
    return Region(**kwargs)
