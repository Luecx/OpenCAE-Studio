from opencae.ui.actions.ids import A
from .specs import RibbonGroupSpec


def groups():
    return (
        RibbonGroupSpec("SECTIONS", (A.SECTION_SOLID, A.SECTION_SHELL, A.SECTION_BEAM, A.SECTION_TRUSS)),
        RibbonGroupSpec("PROFILES", (
            A.PROFILE_RECTANGLE, A.PROFILE_BOX, A.PROFILE_PIPE, A.PROFILE_I,
            A.PROFILE_CHANNEL, A.PROFILE_GENERAL, A.PROFILE_GRAPH,
        )),
    )
