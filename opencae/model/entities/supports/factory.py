from .base import Support
from .displacement import DisplacementSupport
from .fixed import FixedSupport
from .remote_displacement import RemoteDisplacementSupport
from .symmetry import SymmetrySupport
from .temperature import TemperatureSupport

_TYPES = {
    "Fixed": FixedSupport,
    "Displacement": DisplacementSupport,
    "Symmetry": SymmetrySupport,
    "Remote displacement": RemoteDisplacementSupport,
    "Temperature": TemperatureSupport,
}


def create_support(support_type: str, **kwargs) -> Support:
    cls = _TYPES.get(support_type, Support)
    if cls is Support:
        return cls(support_type=support_type, **kwargs)
    return cls(**kwargs)
