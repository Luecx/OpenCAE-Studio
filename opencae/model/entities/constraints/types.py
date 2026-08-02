from enum import StrEnum


class ConstraintType(StrEnum):
    KINEMATIC = "Kinematic Coupling"
    DISTRIBUTING = "Distributing Coupling"
    TIE = "Tie"
    RIGID_BODY = "Rigid Body"
    EQUATION = "Equation"
    MPC = "MPC"

    @classmethod
    def coerce(cls, value):
        try: return cls(value)
        except ValueError: return value


class ConstraintReferenceKind(StrEnum):
    REFERENCE_POINT = "Reference Point"
    NODE_SET = "Node Set"
    ELEMENT_SET = "Element Set"
    SURFACE = "Surface"
    UNKNOWN = "Unknown"

    @classmethod
    def coerce(cls, value):
        try: return cls(value)
        except ValueError: return cls.UNKNOWN
