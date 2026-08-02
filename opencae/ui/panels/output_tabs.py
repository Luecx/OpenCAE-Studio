from PyQt6.QtWidgets import QTabWidget

from .deck_panel import DeckPanel
from .jobs_panel import JobsPanel
from .log_panel import LogPanel
from .python_console import PythonConsole


class OutputTabs(QTabWidget):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.setObjectName("OutputPanel")
        self.store = store
        self.log = LogPanel()
        self.jobs = JobsPanel()
        self.deck = DeckPanel()
        self.console = PythonConsole()
        self.addTab(self.log, "Log")
        self.addTab(self.jobs, "Jobs")
        self.addTab(self.deck, "Input Deck")
        self.addTab(self.console, "Python Console")
        store.message.connect(self.log.append_message)
        store.changed.connect(lambda *_: self.jobs.refresh(store.project))
        self.jobs.refresh(store.project)
