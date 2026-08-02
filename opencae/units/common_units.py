COMMON = {
    "pressure": (("Pa", 1.0), ("kPa", 1e3), ("MPa", 1e6), ("GPa", 1e9), ("psi", 6894.757293168), ("ksi", 6894757.293168)),
    "mass": (("g", 1e-3), ("kg", 1.0), ("t", 1e3), ("lbm", 0.45359237)),
    "density": (("kg/m³", 1.0), ("g/cm³", 1e3), ("t/mm³", 1e12), ("lbm/in³", 27679.904710191)),
    "frequency": (("Hz", 1.0), ("kHz", 1e3)),
    "moment": (("N·mm", 1e-3), ("N·m", 1.0), ("kN·m", 1e3), ("lbf·in", 0.1129848290276167)),
}


def recognized_symbol(quantity: str, scale: float) -> str:
    for symbol, candidate in COMMON.get(quantity, ()):
        if abs(scale - candidate) <= max(abs(candidate), 1.0) * 1e-10:
            return symbol
    return ""
