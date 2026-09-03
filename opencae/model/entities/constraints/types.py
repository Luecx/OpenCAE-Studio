from enum import StrEnum


class ConstraintType(StrEnum):
    KINEMATIC = "Kinematic Coupling"
    DISTRIBUTING = "Distributing Coupling"
    TIE = "Tie"
    RIGID_BODY = "Rigid Body"
    CONNECTOR = "Connector"
    EQUATION = "Equation"
    MPC = "MPC"

    @classmethod
    def coerce(cls, value):
        try: return cls(value)
        except ValueError: return value
