"""Provide independent lower docks for jobs, log output, and result time control."""

from PyQt6.QtWidgets import QDockWidget, QVBoxLayout, QWidget

from opencae.ui.core.metrics import OUTPUT_MIN_HEIGHT
from opencae.ui.panels.jobs_panel import JobsPanel
from opencae.ui.panels.log_panel import LogPanel
from opencae.ui.panels.time_manager import TimeManagerPanel


class _WorkspaceDock(QDockWidget):
    """Common geometry and header behavior for lower workspace docks."""

    def __init__(self, title, object_name, widget, parent=None):
        super().__init__(title, parent)
        self.setObjectName(object_name)
        self.panel = widget

        # Use one explicit styled surface behind every lower workspace.  This is
        # more reliable than a dynamic-property selector on the panel itself and
        # prevents Qt from exposing the darker QMainWindow background around the
        # child panel.
        self.surface = QWidget(self)
        self.surface.setObjectName("WorkspaceSurface")
        surface_layout = QVBoxLayout(self.surface)
        surface_layout.setContentsMargins(0, 0, 0, 0)
        surface_layout.setSpacing(0)
        surface_layout.addWidget(widget)
        self.setWidget(self.surface)
        self.setMinimumHeight(OUTPUT_MIN_HEIGHT)

        # When docked, QMainWindow's tab already carries the workspace name.
        # Suppress the second QDockWidget caption so there is only one header.
        # Restore the native caption while floating so the detached window
        # keeps normal drag/close behavior.
        self._docked_title_bar = QWidget(self)
        self._docked_title_bar.setObjectName("WorkspaceDockHiddenTitleBar")
        self._docked_title_bar.setFixedHeight(0)
        self.topLevelChanged.connect(self._sync_title_bar)
        self._sync_title_bar(False)

    def _sync_title_bar(self, floating):
        """Use only the QMainWindow tab while docked and a native title when floating."""
        self.setTitleBarWidget(None if floating else self._docked_title_bar)


class JobsDock(_WorkspaceDock):
    """Host solver jobs as an independently toggleable dock."""

    def __init__(self, store, jobs, actions, parent=None):
        panel = JobsPanel(store, jobs, actions)
        super().__init__("Jobs", "JobsDock", panel, parent)


class LogDock(_WorkspaceDock):
    """Host application messages as an independently toggleable dock."""

    def __init__(self, store, parent=None):
        panel = LogPanel()
        super().__init__("Log", "LogDock", panel, parent)
        store.message.connect(self.panel.append_message)


class TimeManagerDock(_WorkspaceDock):
    """Host result playback and interpolation controls in their own dock."""

    def __init__(self, parent=None, *, results_page=None, viewport=None):
        panel = TimeManagerPanel(results_page, viewport)
        # TimeManagerPanel historically styled this as a card.  In the docked
        # workspace it belongs directly to the same surface as the tab strip.
        panel.sidebar.setStyleSheet(
            "QFrame#TimeManagerSidebar { background: transparent; border: none; }"
        )
        super().__init__("Time Manager", "TimeManagerDock", panel, parent)
        # Compatibility for callers/tests that historically addressed the
        # panel through ``output_dock.time_manager``.
        self.time_manager = self.panel
