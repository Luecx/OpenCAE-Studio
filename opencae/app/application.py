"""Creates and runs the OpenCAE Qt application with immediate startup feedback."""

from __future__ import annotations

import sys

from .qt_platform import configure_qt_platform_environment

# QPA selection must precede all Qt/VTK imports.
configure_qt_platform_environment()

from PyQt6.QtWidgets import QApplication

from .startup_window import StartupWindow


def _progress(app: QApplication, startup: StartupWindow, value: int, text: str) -> None:
    """Paint one startup milestone before continuing synchronous initialization."""
    startup.set_progress(value, text)
    app.processEvents()


def run() -> int:
    """Create QApplication, show startup feedback, then build the full main window."""
    # Keep heavyweight OpenCAE UI, PyVista, and VTK imports below the first
    # visible Qt surface. This avoids several seconds of apparently dead startup.
    from .app_icon import application_icon, set_windows_app_id

    set_windows_app_id()
    app = QApplication(sys.argv)
    app.setApplicationName("OpenCAE Studio")
    app.setOrganizationName("OpenCAE")

    startup = StartupWindow()
    startup.show()
    _progress(app, startup, 8, "Starting application…")

    from opencae.ui.core.dialog_form_polisher import DialogFormPolisher
    from opencae.ui.core.theme import stylesheet

    app.setWindowIcon(application_icon())
    app.setStyle("Fusion")
    app.setStyleSheet(stylesheet())
    app._dialog_form_polisher = DialogFormPolisher(app)
    app.installEventFilter(app._dialog_form_polisher)
    _progress(app, startup, 28, "Loading interface…")

    from .context import AppContext

    context = AppContext.create()
    _progress(app, startup, 48, "Initializing project services…")

    # MainWindow transitively imports the viewport stack and therefore PyVista/
    # VTK. The startup window is already painted while those imports complete.
    from .main_window import MainWindow

    _progress(app, startup, 66, "Preparing 3D viewport…")
    window = MainWindow(context)
    _progress(app, startup, 94, "Finalizing workspace…")

    # Do not expose two top-level OpenCAE windows in the same compositor frame.
    # In particular, an always-on-top/tool splash overlapping the native QVTK
    # child caused desktop-wide flashing on some X11/XWayland setups.
    startup.set_progress(100, "Ready")
    app.processEvents()
    startup.hide()
    window.show()
    startup.deleteLater()
    return app.exec()
