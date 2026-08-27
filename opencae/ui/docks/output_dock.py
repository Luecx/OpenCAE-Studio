"""Host the lower Output and Time Manager workspace."""

from PyQt6.QtWidgets import QDockWidget, QTabWidget

from opencae.ui.core.metrics import OUTPUT_MIN_HEIGHT
from opencae.ui.panels.output_tabs import OutputTabs
from opencae.ui.panels.time_manager import TimeManagerPanel


class OutputDock(QDockWidget):
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
        super().__init__("Output", parent)
        self.setObjectName("OutputDock")
        self.workspace = QTabWidget()
        self.workspace.setObjectName("OutputWorkspace")
        self.workspace.setDocumentMode(True)
        self.tabs = OutputTabs(store, jobs, actions)
        self.time_manager = TimeManagerPanel(results_page, viewport)
        self.workspace.addTab(self.tabs, "Output")
        self.workspace.addTab(self.time_manager, "Time Manager")
        self.setWidget(self.workspace)
        self.setMinimumHeight(OUTPUT_MIN_HEIGHT)
