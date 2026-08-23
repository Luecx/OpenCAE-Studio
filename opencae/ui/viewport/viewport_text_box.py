"""Styles VTK text actors as readable OpenCAE viewport badges."""

from opencae.ui.core.theme import PALETTE


def apply_viewport_text_box(actor) -> None:
    """Apply a translucent palette-backed rectangle to one VTK text actor."""
    text_property = actor.GetTextProperty()
    text_property.SetColor(*_rgb(PALETTE["text"]))
    text_property.SetBackgroundColor(*_rgb(PALETTE["panel"]))
    text_property.SetBackgroundOpacity(0.92)
    text_property.SetFrame(True)
    text_property.SetFrameColor(*_rgb(PALETTE["border_light"]))
    text_property.SetFrameWidth(1)


def _rgb(color: str) -> tuple[float, float, float]:
    """Convert one hexadecimal palette color to normalized RGB components."""
    value = str(color).lstrip("#")
    return tuple(int(value[index:index + 2], 16) / 255.0 for index in (0, 2, 4))
