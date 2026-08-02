from .base import Section
from .beam import BeamSection
from .shell import ShellSection
from .solid import SolidSection
from .truss import TrussSection

_TYPES = {"Solid": SolidSection, "Shell": ShellSection, "Beam": BeamSection, "Truss": TrussSection}


def create_section(section_type: str, **kwargs) -> Section:
    cls = _TYPES.get(section_type)
    if cls is None:
        return Section(section_type=section_type, **kwargs)
    return cls(**kwargs)
