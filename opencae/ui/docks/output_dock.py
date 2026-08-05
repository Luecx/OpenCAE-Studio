"""Hosts the lower log, job, deck and console area."""

from PyQt6.QtWidgets import QDockWidget

from opencae.ui.core.metrics import OUTPUT_MIN_HEIGHT
from opencae.ui.panels.output_tabs import OutputTabs


class OutputDock(QDockWidget):
    def __init__(self, store, jobs, actions, parent=None):
        super().__init__("Output", parent)
        self.setObjectName("OutputDock")
        self.tabs = OutputTabs(store, jobs, actions)
        self.setWidget(self.tabs)
        self.setMinimumHeight(OUTPUT_MIN_HEIGHT)
