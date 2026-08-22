"""Build the lower output area around Jobs and application log output."""

from PyQt6.QtWidgets import QTabWidget

from .jobs_panel import JobsPanel
from .log_panel import LogPanel


class OutputTabs(QTabWidget):
    def __init__(self, store, jobs, actions, parent=None):
        super().__init__(parent)
        self.setObjectName("OutputPanel")
        self.store = store
        self.log = LogPanel()
        self.jobs = JobsPanel(store, jobs, actions)
        self.addTab(self.jobs, "Jobs")
        self.addTab(self.log, "Log")
        store.message.connect(self.log.append_message)
