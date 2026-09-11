from opencae.model.selection import RegionProjection
from .region import ElementRegion, GeometryRegion, NodeRegion, Region, SurfaceRegion


def create_region(region_type: str = "Region", **kwargs) -> Region:
    """Create the strongest public region type expressible by the request."""
    text = str(region_type or "Region").strip().lower().replace(" ", "_")
    explicit = {
        "geometry": GeometryRegion,
        "geometry_region": GeometryRegion,
        "node": NodeRegion,
        "nodes": NodeRegion,
        "node_region": NodeRegion,
        "node_set": NodeRegion,
        "nodeset": NodeRegion,
        "element": ElementRegion,
        "elements": ElementRegion,
        "element_region": ElementRegion,
        "element_set": ElementRegion,
        "elementset": ElementRegion,
        "surface": SurfaceRegion,
        "facets": SurfaceRegion,
        "surface_region": SurfaceRegion,
    }
    if text in explicit:
        return explicit[text](**kwargs)

    projection = RegionProjection.coerce(kwargs.get("preferred_projection"))
    if projection is RegionProjection.NODES:
        kwargs.pop("preferred_projection", None)
        return NodeRegion(**kwargs)
    if projection is RegionProjection.ELEMENTS:
        kwargs.pop("preferred_projection", None)
        return ElementRegion(**kwargs)
    if projection is RegionProjection.FACETS:
        kwargs.pop("preferred_projection", None)
        return SurfaceRegion(**kwargs)

    if text == "region":
        if projection is None:
            raise ValueError(
                "Region creation requires an explicit node, element, surface, "
                "or geometry type"
            )
        return Region(**kwargs)
    raise ValueError(f"Unknown region type: {region_type!r}")
