"""Provides the canonical compact button used by viewport toolbars."""

from PyQt6.QtWidgets import QToolButton, QWidget


VIEWPORT_TOOL_HEIGHT = 28


class ViewportToolButton(QToolButton):
    """Render one consistently sized action or mode in a viewport toolbar."""

    def __init__(
        self,
        text: str,
        *,
        checkable: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize text, check behavior, and canonical toolbar geometry."""
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(checkable)
        self.setProperty("viewportTool", True)
        self.setFixedHeight(VIEWPORT_TOOL_HEIGHT)
