from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from opencae.ui.core.theme import stylesheet
from .context import AppContext
from .main_window import MainWindow


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("OpenCAE Studio")
    app.setOrganizationName("OpenCAE")
    app.setStyle("Fusion")
    app.setStyleSheet(stylesheet())
    window = MainWindow(AppContext.create())
    window.show()
    return app.exec()
