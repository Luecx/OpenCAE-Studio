from opencae.ui.other.actions.ids import A
from .specs import RibbonGroupSpec


def groups():
    return (RibbonGroupSpec("FIELDS", (A.FIELD,)),)
