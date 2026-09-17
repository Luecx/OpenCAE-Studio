"""Provides the non-editable Qt widget that hosts a profile vector preview."""

from __future__ import annotations

from collections.abc import Mapping

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QPainter, QPaintEvent
from PyQt6.QtWidgets import QSizePolicy, QWidget

from .profile_preview_renderer import render_profile_preview


class ProfilePreviewWidget(QWidget):
    """Hold preview state and repaint it through the profile renderer dispatcher."""

    def __init__(
        self,
        profile_type: str = "General",
        dimensions: Mapping | None = None,
        parent=None,
    ):
        """Create a passive, horizontally expanding technical preview surface."""
        super().__init__(parent)
        self._profile_type = str(profile_type)
        self._dimensions = dict(dimensions or {})
        self.setMinimumHeight(210)
        self.setMaximumHeight(260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    @property
    def profile_type(self) -> str:
        """Return the profile type currently represented by the widget."""
        return self._profile_type

    @property
    def dimensions(self) -> dict:
        """Return a copy of the current renderer-only dimension payload."""
        return dict(self._dimensions)

    def set_profile_type(self, profile_type: str) -> None:
        """Replace the rendered profile type and schedule a repaint."""
        self.set_profile_state(profile_type, self._dimensions)

    def set_dimensions(self, dimensions: Mapping) -> None:
        """Replace the rendered dimensions and schedule a repaint."""
        self.set_profile_state(self._profile_type, dimensions)

    def set_profile_state(self, profile_type: str, dimensions: Mapping) -> None:
        """Atomically replace type and dimensions before scheduling one repaint."""
        self._profile_type = str(profile_type)
        self._dimensions = dict(dimensions)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Render the current immutable snapshot as a fitted vector drawing."""
        painter = QPainter(self)
        render_profile_preview(
            painter,
            QRectF(self.rect()),
            self._profile_type,
            self._dimensions,
        )
        painter.end()
        event.accept()
