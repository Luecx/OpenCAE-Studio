from PyQt6.QtWidgets import QDockWidget

from opencae.ui.core.metrics import OUTPUT_MIN_HEIGHT
from opencae.ui.panels.output_tabs import OutputTabs


class OutputDock(QDockWidget):
    def __init__(self, store, parent=None):
        super().__init__("Output", parent)
        self.setObjectName("OutputDock")
        self.tabs = OutputTabs(store)
        self.setWidget(self.tabs)
        self.setMinimumHeight(OUTPUT_MIN_HEIGHT)
