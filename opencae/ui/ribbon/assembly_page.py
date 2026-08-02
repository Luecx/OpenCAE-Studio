from opencae.ui.actions.ids import A
from .specs import RibbonGroupSpec


def groups():
    return (
        RibbonGroupSpec("INSTANCES", (A.ADD_INSTANCE, A.DUPLICATE_INSTANCE, A.TRANSFORM_INSTANCE, A.SUPPRESS_INSTANCE)),
        RibbonGroupSpec("REGIONS", (A.ASM_NODE_SET, A.ASM_ELEMENT_SET, A.ASM_SURFACE, A.ASM_RP, A.ASM_CSYS)),
    )
