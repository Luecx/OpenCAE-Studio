from PyQt6.QtWidgets import QDockWidget

from opencae.ui.core.metrics import DOCK_MIN_WIDTH
from opencae.ui.tree.project_panel import ProjectPanel


class ProjectDock(QDockWidget):
    def __init__(self, store, actions, visibility=None, parent=None):
        super().__init__("Browser", parent)
        self.setObjectName("ProjectDock")
        self.panel = ProjectPanel(store, actions, visibility=visibility)
        self.tree = self.panel.tree
        self.solution_tree = self.panel.solution_tree
        self.setWidget(self.panel)
        self.setMinimumWidth(DOCK_MIN_WIDTH)
