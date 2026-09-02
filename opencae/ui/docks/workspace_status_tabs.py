"""Provide compact upward-facing toggles for the lower workspace in the status bar."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QToolButton, QWidget


class WorkspaceStatusTabs(QWidget):
    """Expose Jobs, Log, and Time Manager without consuming viewport height."""

    activated = pyqtSignal(str)

    _ITEMS = (
        ("jobs", "Jobs"),
        ("log", "Log"),
        ("time_manager", "Time Manager"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WorkspaceStatusTabs")
        self.buttons = {}
        self._active = "jobs"
        self._expanded = True

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(0)

        for key, text in self._ITEMS:
            button = QToolButton(self)
            button.setText(text)
            button.setCheckable(True)
            button.setAutoRaise(False)
            button.setProperty("workspaceStatusTab", True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _checked=False, value=key: self.activated.emit(value)
            )
            self.buttons[key] = button
            layout.addWidget(button)

        # Keep the workspace tabs as one compact cluster on the left while the
        # contextual Time Manager readout sits at the far right of this status
        # region instead of visually attaching itself to the Time Manager tab.
        layout.addStretch(1)
        self.frame_summary = QLabel(self)
        self.frame_summary.setObjectName("WorkspaceFrameSummary")
        self.frame_summary.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.frame_summary.setVisible(False)
        layout.addWidget(self.frame_summary)
        self.set_state(self._active, self._expanded)

    def set_state(self, active: str, expanded: bool) -> None:
        """Synchronize checked state without relying on QAction/QDockWidget quirks."""
        self._active = str(active)
        self._expanded = bool(expanded)
        for key, button in self.buttons.items():
            button.blockSignals(True)
            button.setChecked(self._expanded and key == self._active)
            button.blockSignals(False)
        self.frame_summary.setVisible(
            self._expanded and self._active == "time_manager"
        )

    def set_frame_summary(self, total, current) -> None:
        """Show the Time Manager's existing textual frame readout at the right edge."""
        total_text = str(total or "0")
        current_text = str(current or "—")
        self.frame_summary.setText(f"Frame {current_text} / {total_text}")
        self.frame_summary.setVisible(
            self._expanded and self._active == "time_manager"
        )
