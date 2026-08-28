"""Provide independent lower docks for jobs, log output, and result time control."""

from PyQt6.QtWidgets import QDockWidget

from opencae.ui.core.metrics import OUTPUT_MIN_HEIGHT
from opencae.ui.panels.jobs_panel import JobsPanel
from opencae.ui.panels.log_panel import LogPanel
from opencae.ui.panels.time_manager import TimeManagerPanel


class _WorkspaceDock(QDockWidget):
    """Common geometry for lower workspace docks."""

    def __init__(self, title, object_name, widget, parent=None):
        super().__init__(title, parent)
        self.setObjectName(object_name)
        self.setWidget(widget)
        self.setMinimumHeight(OUTPUT_MIN_HEIGHT)


class JobsDock(_WorkspaceDock):
    """Host solver jobs as an independently toggleable dock."""

    def __init__(self, store, jobs, actions, parent=None):
        self.panel = JobsPanel(store, jobs, actions)
        super().__init__("Jobs", "JobsDock", self.panel, parent)


class LogDock(_WorkspaceDock):
    """Host application messages as an independently toggleable dock."""

    def __init__(self, store, parent=None):
        self.panel = LogPanel()
        super().__init__("Log", "LogDock", self.panel, parent)
        store.message.connect(self.panel.append_message)


class TimeManagerDock(_WorkspaceDock):
    """Host result playback and interpolation controls in their own dock."""

    def __init__(self, parent=None, *, results_page=None, viewport=None):
        self.panel = TimeManagerPanel(results_page, viewport)
        super().__init__("Time Manager", "TimeManagerDock", self.panel, parent)
        # Compatibility for callers/tests that historically addressed the
        # panel through ``output_dock.time_manager``.
        self.time_manager = self.panel
