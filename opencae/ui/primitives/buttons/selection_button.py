"""Persistent viewport-picking action button."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from opencae.ui.core.metrics import PRIMARY_CONTROL_HEIGHT

from .presentation import ButtonPresentation
from .toggle_button import ToggleButton


class SelectionButton(ToggleButton):
    """Represent an active/inactive viewport selection session.

    This is deliberately distinct from a generic boolean toggle: its checked
    state means a transient interaction session is currently owning viewport
    input.  The optional active caption keeps that lifecycle visible to users.
    """

    def __init__(
        self,
        text: str,
        *,
        active_text: str | None = None,
        tooltip: str = "",
        object_name: str = "InlinePickButton",
        parent: QWidget | None = None,
    ) -> None:
        self._inactive_text = str(text)
        self._active_text = str(active_text) if active_text is not None else None
        super().__init__(
            text=self._inactive_text,
            tooltip=tooltip,
            presentation=ButtonPresentation.DEFAULT,
            object_name=object_name,
            parent=parent,
        )
        self.setProperty("inlineAction", True)
        self.setFixedHeight(PRIMARY_CONTROL_HEIGHT)
        if self._active_text is not None:
            self.toggled.connect(self._sync_caption)

    def _sync_caption(self, active: bool) -> None:
        self.setText(
            self._active_text if active and self._active_text is not None else self._inactive_text
        )
