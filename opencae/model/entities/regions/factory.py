from .element_set import ElementSet
from .node_set import NodeSet
from .region import Region
from .surface import Surface

_TYPES = {
    "Node Set": NodeSet,
    "Element Set": ElementSet,
    "Surface": Surface,
}


def create_region(region_type: str, **kwargs) -> Region:
    cls = _TYPES.get(region_type, Region)
    if cls is Region:
        return cls(region_type=region_type, **kwargs)
    return cls(**kwargs)
