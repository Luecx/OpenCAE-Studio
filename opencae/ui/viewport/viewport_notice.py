"""Renders centered informational notices over the 3D viewport."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout

from opencae.ui.core.theme import PALETTE


class ViewportNotice(QFrame):
    """Reusable centered viewport message using the same panel visual language."""

    def __init__(self, parent=None):
        """Create the notice title and wrapped explanatory text."""
        super().__init__(parent)
        self.setObjectName("ViewportNotice")
        self.setFixedWidth(440)
        self.setStyleSheet(
            f"""
            QFrame#ViewportNotice {{
                background:{PALETTE['panel']};
                border:1px solid {PALETTE['border_light']};
                border-radius:7px;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)
        self.title = QLabel()
        self.title.setStyleSheet(
            f"color:{PALETTE['text']};font-weight:600;font-size:11pt;"
        )
        self.body = QLabel()
        self.body.setWordWrap(True)
        self.body.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.body.setStyleSheet(f"color:{PALETTE['muted']};")
        layout.addWidget(self.title)
        layout.addWidget(self.body)
        self.hide()

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
