from dataclasses import dataclass


@dataclass(frozen=True)
class Quantity:
    key: str
    label: str
    dimensions: tuple[int, int, int, int]


QUANTITIES = (
    Quantity("length", "Length", (1, 0, 0, 0)),
    Quantity("area", "Area", (2, 0, 0, 0)),
    Quantity("volume", "Volume", (3, 0, 0, 0)),
    Quantity("force", "Force", (0, 1, 0, 0)),
    Quantity("moment", "Moment / Energy", (1, 1, 0, 0)),
    Quantity("pressure", "Pressure / Stress", (-2, 1, 0, 0)),
    Quantity("line_load", "Line Load", (-1, 1, 0, 0)),
    Quantity("volume_load", "Volume Load", (-3, 1, 0, 0)),
    Quantity("stiffness", "Translational Stiffness", (-1, 1, 0, 0)),
    Quantity("mass", "Mass", (-1, 1, 2, 0)),
    Quantity("density", "Density", (-4, 1, 2, 0)),
    Quantity("inertia", "Mass Moment of Inertia", (1, 1, 2, 0)),
    Quantity("velocity", "Velocity", (1, 0, -1, 0)),
    Quantity("acceleration", "Acceleration", (1, 0, -2, 0)),
    Quantity("frequency", "Frequency", (0, 0, -1, 0)),
    Quantity("temperature", "Temperature", (0, 0, 0, 1)),
    Quantity("thermal_expansion", "Thermal Expansion", (0, 0, 0, -1)),
    Quantity("section_inertia", "Section Moment of Inertia", (4, 0, 0, 0)),
)
BY_KEY = {item.key: item for item in QUANTITIES}
