from opencae.ui.actions.ids import A
from .specs import RibbonGroupSpec


def groups():
    return (RibbonGroupSpec("NEW SECTION", (A.SECTION_SOLID, A.SECTION_SHELL, A.SECTION_BEAM, A.SECTION_TRUSS)),)
