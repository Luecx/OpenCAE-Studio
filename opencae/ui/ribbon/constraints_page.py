from opencae.ui.actions.ids import A
from .specs import RibbonGroupSpec


def groups():
    return (RibbonGroupSpec("CONSTRAINTS", (
        A.CONSTRAINT_KINEMATIC, A.CONSTRAINT_DISTRIBUTING, A.CONSTRAINT_TIE,
        A.CONSTRAINT_RIGID, A.CONSTRAINT_CONNECTOR, A.CONSTRAINT_EQUATION,
        A.CONSTRAINT_MPC,
    )),)
