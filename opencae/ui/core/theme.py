from __future__ import annotations

from .styles import STYLE_MODULES

PALETTE = {
    "window": "#171a1f",
    "panel": "#1d2127",
    "panel_alt": "#22272e",
    "panel_hover": "#29313a",
    "border": "#303741",
    "border_light": "#3a424d",
    "text": "#e5e9ef",
    "muted": "#98a2ad",
    "accent": "#3296e6",
    "accent_hover": "#43a6f5",
    "accent_dim": "#173d5b",
    "selection": "#173d5b",
    "success": "#49b675",
    "warning": "#d5a442",
    "danger": "#df6262",
    "viewport": "#101319",
}


def stylesheet() -> str:
    return "\n".join(module.css(PALETTE) for module in STYLE_MODULES)
