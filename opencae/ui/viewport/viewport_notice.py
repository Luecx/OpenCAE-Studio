"""Renders centered informational notices over the 3D viewport."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout

from opencae.ui.core.theme import PALETTE


class ViewportNotice(QFrame):
    """Reusable centered viewport message using the same panel visual language."""

    def __init__(self, parent=None):
        """Create the notice title and wrapped explanatory text."""
        super().__init__(parent)
        self.setObjectName("ViewportNotice")
        # Rounded Qt widgets sit above a native OpenGL surface. Transparent corner
        # pixels can therefore expose the platform's native black backing store
        # instead of the VTK image. Paint the complete widget as viewport first;
        # the rounded QSS panel is drawn on top and leaves matching corner pixels.
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setFixedWidth(440)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)
        self.title = QLabel()
        self.body = QLabel()
        self.body.setWordWrap(True)
        self.body.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.title)
        layout.addWidget(self.body)
        self.refresh_theme()
        self.hide()

    def paintEvent(self, event) -> None:
        """Provide deterministic viewport-colored pixels outside rounded corners."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(PALETTE["viewport"]))
        painter.end()
        super().paintEvent(event)

    def refresh_theme(self) -> None:
        self.setStyleSheet(
            f"QFrame#ViewportNotice{{background:{PALETTE['overlay_bg']};"
            f"border:1px solid {PALETTE['overlay_border']};border-radius:7px;}}"
        )
        self.title.setStyleSheet(
            f"color:{PALETTE['overlay_text']};font-weight:600;font-size:11pt;"
        )
        self.body.setStyleSheet(f"color:{PALETTE['muted']};")

    def set_message(self, title: str, body: str) -> None:
        """Show one title/body notice and resize to its wrapped contents."""
        self.title.setText(str(title))
        self.body.setText(str(body))
        self.adjustSize()
        self.show()
        self.raise_()

    def clear(self) -> None:
        """Hide the current notice."""
        self.hide()
