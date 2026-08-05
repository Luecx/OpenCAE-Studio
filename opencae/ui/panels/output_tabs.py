"""Builds the lower output area around the central Jobs panel."""

from PyQt6.QtWidgets import QTabWidget

from .deck_panel import DeckPanel
from .jobs_panel import JobsPanel
from .log_panel import LogPanel
from .python_console import PythonConsole


class OutputTabs(QTabWidget):
    def __init__(self, store, jobs, actions, parent=None):
        super().__init__(parent)
        self.setObjectName("OutputPanel")
        self.store = store
        self.log = LogPanel()
        self.jobs = JobsPanel(store, jobs, actions)
        self.deck = DeckPanel()
        self.console = PythonConsole()
        self.addTab(self.jobs, "Jobs")
        self.addTab(self.log, "Log")
        self.addTab(self.deck, "Input Deck")
        self.addTab(self.console, "Python Console")
        store.message.connect(self.log.append_message)
