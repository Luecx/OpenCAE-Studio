from opencae.ui.actions.ids import A
from opencae.ui.actions.spec import ActionSpec
from opencae.ui.core.icon_factory import IconKind as I


def specs(c):
    return (
        ActionSpec(A.FIXED, "Fixed", I.FIXED_SUPPORT, lambda: c.loads.support("Fixed")),
        ActionSpec(A.DISPLACEMENT, "Displacement", I.DISPLACEMENT_SUPPORT, lambda: c.loads.support("Displacement")),
        ActionSpec(A.SYMMETRY, "Symmetry", I.SYMMETRY_SUPPORT, lambda: c.loads.support("Symmetry")),
        ActionSpec(A.AMPLITUDE, "Amplitude", I.FIELD, c.loads.amplitude),
        ActionSpec(A.CLOAD, "Concentrated", I.CONCENTRATED_LOAD, lambda: c.loads.load("Concentrated Load")),
        ActionSpec(A.DLOAD, "Traction", I.TRACTION_LOAD, lambda: c.loads.load("Surface Traction")),
        ActionSpec(A.PRESSURE, "Pressure", I.PRESSURE_LOAD, lambda: c.loads.load("Pressure")),
        ActionSpec(A.VLOAD, "Volume", I.VOLUME_LOAD, lambda: c.loads.load("Volume Load")),
        ActionSpec(A.INERTIA_LOAD, "Inertia", I.INERTIA_LOAD, lambda: c.loads.load("Inertia Load")),
        ActionSpec(A.TEMPERATURE, "Temperature", I.TEMPERATURE_LOAD, lambda: c.loads.load("Temperature")),
    )
