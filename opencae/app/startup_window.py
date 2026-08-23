"""Owns the lightweight borderless startup window shown before heavy GUI imports."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget


class StartupWindow(QWidget):
    """Small frameless startup surface that remains responsive during initialization."""

    def __init__(self):
        """Create the startup title, status label, and progress bar."""
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setObjectName("StartupWindow")
        self.setFixedSize(520, 210)
        self.setStyleSheet(
            """
            QWidget#StartupWindow {
                background: #20252b;
                border: 1px solid #4b5560;
                border-radius: 10px;
            }
            QLabel { color: #e8edf2; border: none; }
            QLabel#StartupTitle { font-size: 24px; font-weight: 700; }
            QLabel#StartupStatus { color: #aeb8c2; }
            QProgressBar {
                min-height: 8px;
                max-height: 8px;
                border: none;
                border-radius: 4px;
                background: #343b43;
                text-align: center;
            }
            QProgressBar::chunk {
                border-radius: 4px;
                background: #4da3ff;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)
        title = QLabel("OpenCAE Studio")
        title.setObjectName("StartupTitle")
        layout.addWidget(title)
        layout.addStretch(1)
        self.status = QLabel("Starting…")
        self.status.setObjectName("StartupStatus")
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

    def showEvent(self, event) -> None:
        """Center the startup window when it first becomes visible."""
        super().showEvent(event)
        screen = self.screen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        self.move(
            geometry.center().x() - self.width() // 2,
            geometry.center().y() - self.height() // 2,
        )

    def set_progress(self, value: int, message: str) -> None:
        """Update startup progress and the user-facing initialization message."""
        self.progress.setValue(max(0, min(100, int(value))))
        self.status.setText(str(message))
