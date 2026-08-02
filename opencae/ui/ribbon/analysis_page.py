from opencae.ui.actions.ids import A
from .specs import RibbonGroupSpec


def groups():
    return (
        RibbonGroupSpec("NEW STEP", (A.STEP_LINEAR, A.STEP_NONLINEAR, A.STEP_MODAL, A.STEP_BUCKLING, A.STEP_TRANSIENT)),
        RibbonGroupSpec("MANAGE", (A.REORDER_STEPS, A.STEP_MATRIX)),
    )
