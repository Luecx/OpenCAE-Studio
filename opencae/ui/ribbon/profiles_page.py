from opencae.ui.actions.ids import A
from .specs import RibbonGroupSpec


def groups():
    return (RibbonGroupSpec("NEW PROFILE", (
        A.PROFILE_RECTANGLE, A.PROFILE_BOX, A.PROFILE_PIPE, A.PROFILE_I,
        A.PROFILE_CHANNEL, A.PROFILE_U, A.PROFILE_H, A.PROFILE_CIRCLE, A.PROFILE_GENERAL, A.PROFILE_GRAPH,
    )),)
