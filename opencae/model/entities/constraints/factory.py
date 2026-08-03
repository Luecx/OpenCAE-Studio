from .base import Constraint
from .distributing_coupling import DistributingCoupling
from .equation import EquationConstraint
from .kinematic_coupling import KinematicCoupling
from .mpc import MPCConstraint
from .rigid_body import RigidBodyConstraint
from .tie import TieConstraint
from .types import ConstraintType

_TYPES = {
    ConstraintType.KINEMATIC: KinematicCoupling,
    ConstraintType.DISTRIBUTING: DistributingCoupling,
    ConstraintType.TIE: TieConstraint,
    ConstraintType.RIGID_BODY: RigidBodyConstraint,
    ConstraintType.EQUATION: EquationConstraint,
    ConstraintType.MPC: MPCConstraint,
}


def create_constraint(constraint_type: ConstraintType | str, **kwargs) -> Constraint:
    kind = ConstraintType.coerce(constraint_type); cls = _TYPES.get(kind, Constraint)
    if cls in {KinematicCoupling, DistributingCoupling} and "master" in kwargs:
        kwargs["control_point"] = kwargs.pop("master")
    elif cls is RigidBodyConstraint:
        if "master" in kwargs: kwargs["reference"] = kwargs.pop("master")
        if "slave" in kwargs: kwargs["body"] = kwargs.pop("slave")
    return cls(**kwargs) if cls is not Constraint else cls(constraint_type=kind, **kwargs)
