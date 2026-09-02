"""Coordinate the movable lower workspace with status-bar tabs and persistence."""

from __future__ import annotations

from PyQt6.QtCore import QObject, QSettings, QTimer, Qt

from opencae.ui.actions.ids import A
from .workspace_status_tabs import WorkspaceStatusTabs


class WorkspaceDockController(QObject):
    """Control one movable dock whose stacked page is selected from the status bar."""

    DEFAULT_HEIGHT = 300
    COLLAPSE_HEIGHT = 48
    ACTIVE_KEY = "bottom_workspace/active"
    EXPANDED_KEY = "bottom_workspace/expanded"
    HEIGHT_KEY = "bottom_workspace/height"

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.dock = window.workspace_dock
        self.active = "jobs"
        self.expanded = True
        self.last_height = self.DEFAULT_HEIGHT
        self._changing = False

        self.tabs = WorkspaceStatusTabs(window.statusBar())
        window.statusBar().insertPermanentWidget(0, self.tabs, 1)
        self.tabs.activated.connect(self.toggle)

        self.dock.collapse_requested.connect(self._collapse_if_small)
        self.dock.visibilityChanged.connect(self._dock_visibility_changed)

        panel = self.dock.time_manager
        panel.frame_summary_changed.connect(self.tabs.set_frame_summary)
        self.tabs.set_frame_summary(
            panel.total_frames.text(),
            panel.current_frame_label.text(),
        )

        self._configure_actions()
        self.dock.set_page("jobs")
        self._sync_controls()

    def toggle(self, name: str) -> None:
        """Open another page, or collapse when the active status tab is clicked."""
        name = str(name)
        if name not in self.dock.pages:
            return
        if self.expanded and self.active == name and self.dock.isVisible():
            self.collapse()
        else:
            self.show(name)

    def show(self, name: str, *, height: int | None = None) -> None:
        """Show one page without changing the dock's current docking/floating position."""
        if name not in self.dock.pages:
            return
        requested_height = max(
            self.COLLAPSE_HEIGHT + 20,
            int(self.last_height if height is None else height),
        )
        self._changing = True
        try:
            self.dock.set_page(name)
            self.dock.show()
            self.dock.raise_()
            if self._is_horizontal_dock_area() and not self.dock.isFloating():
                self.window.resizeDocks(
                    [self.dock],
                    [requested_height],
                    Qt.Orientation.Vertical,
                )
        finally:
            self._changing = False
        self.active = name
        self.expanded = True
        self.last_height = requested_height
        self._sync_controls()

    def collapse(self) -> None:
        """Hide the workspace while leaving its status tabs available to restore it."""
        if not self.expanded:
            return
        if (
            self._is_horizontal_dock_area()
            and not self.dock.isFloating()
            and self.dock.height() > self.COLLAPSE_HEIGHT
        ):
            self.last_height = max(self.DEFAULT_HEIGHT // 2, int(self.dock.height()))
        self._changing = True
        try:
            self.dock.hide()
        finally:
            self._changing = False
        self.expanded = False
        self._sync_controls()

    def reset(self) -> None:
        """Restore the default bottom-docked expanded Jobs workspace."""
        self.last_height = self.DEFAULT_HEIGHT
        self.show("jobs", height=self.DEFAULT_HEIGHT)

    def save_state(self, settings: QSettings) -> None:
        """Persist active page, collapse state, and last useful bottom-dock height."""
        settings.setValue(self.ACTIVE_KEY, self.active)
        settings.setValue(self.EXPANDED_KEY, self.expanded and self.dock.isVisible())
        settings.setValue(self.HEIGHT_KEY, self.last_height)

    def restore_state(self, settings: QSettings) -> None:
        """Restore the page/collapse state after QMainWindow restores dock placement."""
        active = str(settings.value(self.ACTIVE_KEY, "jobs") or "jobs")
        if active not in self.dock.pages:
            active = "jobs"
        expanded = self._bool_value(settings.value(self.EXPANDED_KEY, True), True)
        try:
            height = int(settings.value(self.HEIGHT_KEY, self.DEFAULT_HEIGHT))
        except (TypeError, ValueError):
            height = self.DEFAULT_HEIGHT
        self.last_height = max(self.COLLAPSE_HEIGHT + 20, height)
        self.active = active
        self.dock.set_page(active)
        if expanded:
            self.show(active, height=self.last_height)
        else:
            self._changing = True
            try:
                self.dock.hide()
            finally:
                self._changing = False
            self.expanded = False
            self._sync_controls()

    def _collapse_if_small(self) -> None:
        if self._changing or not self.expanded or self.dock.isFloating():
            return
        if not self._is_horizontal_dock_area():
            return
        if self.dock.height() <= self.COLLAPSE_HEIGHT:
            QTimer.singleShot(0, self.collapse)

    def _dock_visibility_changed(self, visible: bool) -> None:
        """Keep status tabs/actions correct when the native dock close button is used."""
        if self._changing:
            return
        self.expanded = bool(visible)
        if visible:
            self.active = self.dock.active_page
        self._sync_controls()

    def _is_horizontal_dock_area(self) -> bool:
        area = self.window.dockWidgetArea(self.dock)
        return area in {
            Qt.DockWidgetArea.TopDockWidgetArea,
            Qt.DockWidgetArea.BottomDockWidgetArea,
        }

    def _configure_actions(self) -> None:
        action_map = {
            "jobs": A.SHOW_JOBS,
            "log": A.SHOW_LOG,
            "time_manager": A.SHOW_TIME_MANAGER,
        }
        self._workspace_actions = {}
        for name, action_id in action_map.items():
            action = self.window.actions.get(action_id)
            action.setCheckable(True)
            self._workspace_actions[name] = action

        project = self.window.actions.get(A.SHOW_PROJECT)
        project.setCheckable(True)
        project.setChecked(not self.window.project_dock.isHidden())
        self.window.project_dock.visibilityChanged.connect(project.setChecked)

    def _sync_controls(self) -> None:
        self.tabs.set_state(self.active, self.expanded and self.dock.isVisible())
        for name, action in self._workspace_actions.items():
            action.blockSignals(True)
            action.setChecked(
                self.expanded and self.dock.isVisible() and name == self.active
            )
            action.blockSignals(False)

    @staticmethod
    def _bool_value(value, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        if isinstance(value, (int, float)):
            return bool(value)
        return bool(default)
