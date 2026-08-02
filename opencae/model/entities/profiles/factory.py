from .base import Profile
from .box import BoxProfile
from .channel import CProfile
from .circle import CircleProfile
from .general import GeneralProfile
from .graph import GraphProfile
from .h_profile import HProfile
from .i_profile import IProfile
from .pipe import PipeProfile
from .rectangle import RectangleProfile
from .u_profile import UProfile

_TYPES = {
    "Rectangle": RectangleProfile, "Box": BoxProfile, "Pipe": PipeProfile,
    "Circle": CircleProfile, "I-profile": IProfile, "H-profile": HProfile,
    "C-profile": CProfile, "Channel": CProfile, "U-profile": UProfile,
    "General": GeneralProfile, "Graph profile": GraphProfile,
}

def create_profile(profile_type: str, **kwargs) -> Profile:
    cls = _TYPES.get(profile_type, Profile)
    return cls(**kwargs) if cls is not Profile else cls(profile_type=profile_type, **kwargs)
