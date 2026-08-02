from .constraints import COMMANDS as CONSTRAINTS
from .geometry import COMMANDS as GEOMETRY
from .loadcases import COMMANDS as LOADCASES
from .loads import COMMANDS as LOADS
from .properties import COMMANDS as PROPERTIES

ALL_COMMANDS = {spec.name: spec for spec in (*GEOMETRY, *PROPERTIES, *LOADS, *CONSTRAINTS, *LOADCASES)}
