"""Compatibility class for the canonical viewport command button."""

from opencae.ui.core.metrics import VIEWPORT_TOOL_HEIGHT
from opencae.ui.primitives.buttons import ViewportButton


class ViewportToolButton(ViewportButton):
    """Backward-compatible name for the canonical viewport button primitive."""


__all__ = ["VIEWPORT_TOOL_HEIGHT", "ViewportToolButton"]
