from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from opencae.ui.core.dialog_form_polisher import DialogFormPolisher
from opencae.ui.core.theme import stylesheet
from .app_icon import application_icon, set_windows_app_id
from .context import AppContext
from .main_window import MainWindow


def run() -> int:
    set_windows_app_id()
    app = QApplication(sys.argv)
    app.setApplicationName("OpenCAE Studio")
    app.setOrganizationName("OpenCAE")
    app.setWindowIcon(application_icon())
    app.setStyle("Fusion")
    app.setStyleSheet(stylesheet())

    # Keep the filter alive for the lifetime of QApplication. It normalizes all
    # QFormLayout-based dialogs, including stacked selector pages, on show.
    app._dialog_form_polisher = DialogFormPolisher(app)
    app.installEventFilter(app._dialog_form_polisher)

    window = MainWindow(AppContext.create())
    window.show()
    return app.exec()
