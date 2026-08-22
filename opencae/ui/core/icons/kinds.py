from enum import Enum, auto


class IconKind(Enum):
    FILE = auto(); SAVE = auto(); IMPORT = auto(); PART = auto(); PARTITION = auto()
    MESH = auto(); SEED = auto(); ELEMENT = auto(); ELEMENT_CONTROLS = auto(); NODE_SET = auto(); ELEMENT_SET = auto()
    SURFACE = auto(); CSYS = auto(); RP = auto(); MATERIAL = auto(); PROFILE = auto(); SECTION = auto()
    ASSIGN = auto(); INSTANCE = auto(); MOVE = auto(); ROTATE = auto(); PATTERN = auto(); CONSTRAINT = auto()
    CONSTRAINT_KINEMATIC = auto(); CONSTRAINT_DISTRIBUTING = auto(); CONSTRAINT_TIE = auto()
    CONSTRAINT_RIGID = auto(); CONSTRAINT_EQUATION = auto(); CONSTRAINT_MPC = auto()
    SUPPORT = auto(); FIXED_SUPPORT = auto(); DISPLACEMENT_SUPPORT = auto(); SYMMETRY_SUPPORT = auto()
    LOAD = auto(); CONCENTRATED_LOAD = auto(); TRACTION_LOAD = auto(); PRESSURE_LOAD = auto()
    VOLUME_LOAD = auto(); INERTIA_LOAD = auto(); TEMPERATURE_LOAD = auto(); ANALYSIS = auto()
    SETTINGS = auto(); VALIDATE = auto(); DECK = auto(); RUN = auto(); RESULTS = auto(); DELETE = auto(); CLEAR = auto()
    EDIT = auto(); DUPLICATE = auto(); INFO = auto(); ELASTICITY = auto(); DENSITY = auto()
    PLASTICITY = auto(); THERMAL = auto(); FIELD = auto(); SECTION_SOLID = auto(); SECTION_SHELL = auto()
    SECTION_BEAM = auto(); SECTION_TRUSS = auto(); PROFILE_RECTANGLE = auto(); PROFILE_BOX = auto()
    PROFILE_PIPE = auto(); PROFILE_I = auto(); PROFILE_CHANNEL = auto(); PROFILE_U = auto(); PROFILE_H = auto(); PROFILE_CIRCLE = auto(); PROFILE_GENERAL = auto()
    PROFILE_GRAPH = auto(); STEP_LINEAR = auto(); STEP_NONLINEAR = auto(); STEP_MODAL = auto()
    STEP_BUCKLING = auto(); STEP_TRANSIENT = auto(); REORDER = auto(); MATRIX = auto(); CONTOUR = auto()
    RESULT_STEP = auto(); RESULT_FRAME = auto(); RESULT_FIELD = auto(); PREVIOUS_FRAME = auto(); NEXT_FRAME = auto()
    MESH_LINES = auto(); BOUNDARY_LINES = auto(); DEFORMATION = auto(); SECTION_VIEW = auto(); VISIBILITY = auto()
    PICK = auto()
    UNDEFORMED = auto(); QUERY_NODE = auto(); QUERY_ELEMENT = auto(); RANGE = auto()
