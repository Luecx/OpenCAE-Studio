from opencae.ui.actions.ids import A
from .specs import RibbonGroupSpec


def groups():
    return (
        RibbonGroupSpec("SUPPORTS", (A.FIXED, A.DISPLACEMENT, A.SYMMETRY)),
        RibbonGroupSpec("LOADS", (A.CLOAD, A.DLOAD, A.PRESSURE, A.VLOAD, A.INERTIA_LOAD, A.TEMPERATURE)),
        RibbonGroupSpec("AMPLITUDES", (A.AMPLITUDE,)),
    )
