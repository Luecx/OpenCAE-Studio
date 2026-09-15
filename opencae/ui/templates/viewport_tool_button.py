"""Compatibility constructor for canonical viewport command primitives."""

from opencae.ui.core.metrics import VIEWPORT_TOOL_HEIGHT
from opencae.ui.primitives.buttons import ButtonViewportAction, ButtonViewportToggle


def ViewportToolButton(text: str = "", checkable: bool = False, parent=None):
    """Return the concrete viewport primitive matching the requested behavior.

    This compatibility surface preserves the historical constructor used by
    older consumers without reintroducing the removed generic ``ViewportButton``
    hierarchy.
    """
    primitive = ButtonViewportToggle if checkable else ButtonViewportAction
    return primitive(text, parent=parent)


__all__ = ["VIEWPORT_TOOL_HEIGHT", "ViewportToolButton"]
