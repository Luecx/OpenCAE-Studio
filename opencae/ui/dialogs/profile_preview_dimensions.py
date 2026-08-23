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


def parameter_label(key: str, text: str) -> str:
    """Append the drawing symbol to an input label when it adds information."""
    symbol = dimension_symbol(key)
    normalized_text = text.casefold().replace(" ", "")
    if symbol.casefold() == normalized_text:
        return text
    return f"{text} ({symbol})"
