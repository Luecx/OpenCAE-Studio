from opencae.ui.actions.ids import A
from .specs import RibbonGroupSpec


def groups():
    return (RibbonGroupSpec("FIELDS", (A.FIELD,)),)
