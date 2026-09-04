"""Persist and restore the top-level Qt window geometry and dock layout."""

from __future__ import annotations

from PyQt6.QtCore import QByteArray, QObject, QSettings


class WindowStatePersistence(QObject):
    """Own QSettings persistence for one main-window geometry/layout lifecycle."""

    STATE_VERSION = 3
    GEOMETRY_KEY = "main_window/geometry"
    STATE_KEY = "main_window/state"
    STATE_SCHEMA_KEY = "main_window/state_schema"
    RESTORE_KEY = "ui/restore_layout"

    def __init__(self, window, settings=None):
        super().__init__(window if isinstance(window, QObject) else None)
        self.window = window
        self.settings = settings or QSettings()

    def restore(self) -> None:
        """Restore geometry, dock state and workspace state when enabled."""
        if not _bool_value(self.settings.value(self.RESTORE_KEY, True), True):
            return

        geometry = self.settings.value(self.GEOMETRY_KEY)
        if isinstance(geometry, QByteArray) and not geometry.isEmpty():
            self.window.restoreGeometry(geometry)

        try:
            schema = int(self.settings.value(self.STATE_SCHEMA_KEY) or 0)
        except (TypeError, ValueError):
            schema = 0
        state = self.settings.value(self.STATE_KEY)
        if (
            schema == self.STATE_VERSION
            and isinstance(state, QByteArray)
            and not state.isEmpty()
        ):
            self.window.restoreState(state, self.STATE_VERSION)

        workspace = getattr(self.window, "workspace_controller", None)
        if workspace is not None:
            workspace.restore_state(self.settings)

    def save(self) -> None:
        """Persist geometry plus dock, toolbar, and collapsible workspace state."""
        self.settings.setValue(self.GEOMETRY_KEY, self.window.saveGeometry())
        self.settings.setValue(self.STATE_SCHEMA_KEY, self.STATE_VERSION)
        self.settings.setValue(
            self.STATE_KEY,
            self.window.saveState(self.STATE_VERSION),
        )
        workspace = getattr(self.window, "workspace_controller", None)
        if workspace is not None:
            workspace.save_state(self.settings)
        self.settings.sync()


def _bool_value(value, default: bool) -> bool:
    """Normalize QSettings boolean representations."""
    if isinstance(value, bool):
        return value
    if value is None:
        return bool(default)
    return str(value).strip().casefold() not in {"0", "false", "no", "off", ""}
