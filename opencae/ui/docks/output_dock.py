"""Provide one movable lower workspace for jobs, log output, and time control."""

from PyQt6.QtCore import QSize, pyqtSignal
from PyQt6.QtWidgets import QDockWidget, QStackedWidget, QVBoxLayout, QWidget

from opencae.ui.panels.jobs_panel import JobsPanel
from opencae.ui.panels.log_panel import LogPanel
from opencae.ui.panels.time_manager import TimeManagerPanel


class WorkspaceDock(QDockWidget):
    """Host all lower workspaces in one native movable/floating QDockWidget."""

    collapse_requested = pyqtSignal()
    COLLAPSE_HEIGHT = 48

    _TITLES = {
        "jobs": "Jobs",
        "log": "Log",
        "time_manager": "Time Manager",
    }

    def __init__(
        self,
        store,
        jobs,
        actions,
        parent=None,
        *,
        results_page=None,
        viewport=None,
    ):
        super().__init__("Jobs", parent)
        self.setObjectName("WorkspaceDock")
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.setMinimumHeight(0)

        self.jobs = JobsPanel(store, jobs, actions)
        self.log = LogPanel()
        self.time_manager = TimeManagerPanel(results_page, viewport)
        store.message.connect(self.log.append_message)

        # Bias the compact Time Manager controls inward from the window edge
        # while keeping the plot close to the controls.
        self.time_manager.layout().setContentsMargins(10, 3, 2, 4)
        self.time_manager.layout().setSpacing(4)
        self.time_manager.sidebar.layout().setContentsMargins(14, 4, 2, 4)
        self.time_manager.sidebar.setStyleSheet(
            "QFrame#TimeManagerSidebar { background: transparent; border: none; }"
        )

        self.pages = {
            "jobs": self.jobs,
            "log": self.log,
            "time_manager": self.time_manager,
        }
        self.stack = QStackedWidget(self)
        self.stack.setObjectName("WorkspaceStack")
        for widget in self.pages.values():
            widget.setProperty("workspaceSurface", True)
            widget.setMinimumHeight(0)
            self.stack.addWidget(widget)

        self.surface = QWidget(self)
        self.surface.setObjectName("WorkspaceSurface")
        self.surface.setMinimumHeight(0)
        surface_layout = QVBoxLayout(self.surface)
        surface_layout.setContentsMargins(0, 0, 0, 0)
        surface_layout.setSpacing(0)
        surface_layout.addWidget(self.stack)
        self.setWidget(self.surface)

        self.active_page = "jobs"
        self.set_page("jobs")

    def set_page(self, name: str) -> bool:
        """Switch workspace content without changing dock position or ownership."""
        name = str(name)
        page = self.pages.get(name)
        if page is None:
            return False
        self.active_page = name
        self.stack.setCurrentWidget(page)
        self.setWindowTitle(self._TITLES[name])
        return True

    def minimumSizeHint(self):
        """Allow the bottom dock to shrink all the way into the status-bar zone."""
        hint = super().minimumSizeHint()
        return QSize(hint.width(), 0)

    def resizeEvent(self, event):
        """Request collapse when the bottom-docked workspace is dragged very small."""
        super().resizeEvent(event)
        if not self.isFloating() and self.height() <= self.COLLAPSE_HEIGHT:
            self.collapse_requested.emit()
