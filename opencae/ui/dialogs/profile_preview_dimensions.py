"""Maps persisted profile dimension keys to compact drawing symbols."""

from __future__ import annotations


DIMENSION_SYMBOLS = {
    "width": "b",
    "height": "h",
    "thickness": "t",
    "diameter": "d",
    "flange_width": "b",
    "web_thickness": "tw",
    "flange_thickness": "tf",
    "area": "A",
    "iyy": "Iyy",
    "izz": "Izz",
    "iyz": "Iyz",
    "torsion_constant": "It",
}


def dimension_symbol(key: str) -> str:
    """Return the canonical compact label for one existing model key."""
    return DIMENSION_SYMBOLS.get(key, key)
