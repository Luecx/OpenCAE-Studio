from .base import Load
from .concentrated import ConcentratedLoad
from .distributed import DistributedLoad
from .inertia import InertiaLoad
from .pressure import PressureLoad
from .temperature import TemperatureLoad
from .volume import VolumeLoad

_TYPES = {
    "Concentrated Load": ConcentratedLoad,
    "Surface Traction": DistributedLoad,
    "Pressure": PressureLoad,
    "Volume Load": VolumeLoad,
    "Temperature": TemperatureLoad,
    "Inertia Load": InertiaLoad,
}


def create_load(load_type: str, **kwargs) -> Load:
    cls = _TYPES.get(load_type, Load)
    return cls(**kwargs) if cls is not Load else cls(load_type=load_type, **kwargs)
