from dataclasses import dataclass


@dataclass(frozen=True)
class Unit:
    symbol: str
    scale: float
    offset: float = 0.0


LENGTH_UNITS = {
    "m": Unit("m", 1.0), "mm": Unit("mm", 1e-3), "cm": Unit("cm", 1e-2),
    "µm": Unit("µm", 1e-6), "in": Unit("in", 0.0254), "ft": Unit("ft", 0.3048),
}
FORCE_UNITS = {
    "N": Unit("N", 1.0), "kN": Unit("kN", 1e3), "MN": Unit("MN", 1e6),
    "lbf": Unit("lbf", 4.4482216152605), "kip": Unit("kip", 4448.2216152605),
}
TIME_UNITS = {
    "s": Unit("s", 1.0), "ms": Unit("ms", 1e-3), "min": Unit("min", 60.0),
}
TEMPERATURE_UNITS = {
    "K": Unit("K", 1.0, 0.0), "°C": Unit("°C", 1.0, 273.15),
    "°F": Unit("°F", 5.0 / 9.0, 255.3722222222222),
}
BASE_CATALOGS = {
    "length": LENGTH_UNITS, "force": FORCE_UNITS,
    "time": TIME_UNITS, "temperature": TEMPERATURE_UNITS,
}
