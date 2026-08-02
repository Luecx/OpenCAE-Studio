from opencae.ui.actions.ids import A
from .specs import RibbonGroupSpec


def groups():
    return (
        RibbonGroupSpec("MATERIAL", (A.MATERIAL,)),
        RibbonGroupSpec("DEFINITIONS", (A.SET_ELASTICITY, A.SET_DENSITY, A.SET_PLASTICITY, A.SET_THERMAL)),
    )
