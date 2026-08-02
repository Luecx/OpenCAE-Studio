from .system import UnitSystem


def default_systems():
    return [
        UnitSystem("mm-N-s-°C", "mm", "N", "s", "°C"),
        UnitSystem("SI (m-N-s-K)", "m", "N", "s", "K"),
        UnitSystem("mm-kN-s-°C", "mm", "kN", "s", "°C"),
        UnitSystem("Imperial (in-lbf-s-°F)", "in", "lbf", "s", "°F"),
    ]
