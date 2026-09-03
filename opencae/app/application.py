"""Creates and runs the OpenCAE Qt application with immediate startup feedback."""

from __future__ import annotations

import sys

from .qt_platform import configure_qt_platform_environment

# QPA selection must precede all Qt imports. Native selection is the default;
# explicit xcb/wayland overrides remain available for troubleshooting.
configure_qt_platform_environment()

# PyVistaQt's QOpenGLWidget bridge requires one process-wide compatible desktop
# OpenGL format before QApplication and, critically, before any top-level widget
# such as the startup splash is created.
from .qt_opengl import configure_qt_opengl

configure_qt_opengl()

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
    app.setStyle("Fusion")

    # Color preference is intentionally applied before constructing even the
    # lightweight splash. Every widget can therefore read the same process-wide
    # semantic PALETTE at construction time, including custom local painters.
    from opencae.store.app_settings import AppSettings
    from opencae.ui.core.theme import DEFAULT_COLOR_SCHEME, apply_color_scheme

    appearance = AppSettings()
    scheme = apply_color_scheme(
        app,
        appearance.value("appearance/color_scheme", DEFAULT_COLOR_SCHEME),
    )
    appearance.set_value("appearance/color_scheme", scheme)

    startup = StartupWindow()
    startup.show()
    _progress(app, startup, 8, "Starting application…")

    from opencae.ui.core.dialog_form_polisher import DialogFormPolisher

    app.setWindowIcon(application_icon())
    app._dialog_form_polisher = DialogFormPolisher(app)
    app.installEventFilter(app._dialog_form_polisher)
    _progress(app, startup, 26, "Loading interface…")

    from opencae.geometry.gmsh_session import finalize_gmsh, initialize_gmsh

    _progress(app, startup, 38, "Initializing meshing kernel…")
    gmsh_ready = initialize_gmsh()
    if gmsh_ready:
        app.aboutToQuit.connect(finalize_gmsh)

    from .context import AppContext

    context = AppContext.create()
    _progress(app, startup, 50, "Initializing project services…")

    # MainWindow transitively imports the viewport stack and therefore PyVista/
    # VTK. The startup window is already painted while those imports complete.
    from opencae.ui.docks.workspace_controller import WorkspaceDockController
    from .main_window import MainWindow
    from .window_state import WindowStatePersistence

    _progress(app, startup, 68, "Preparing 3D viewport…")
    window = MainWindow(context)
    window.workspace_controller = WorkspaceDockController(window)
    window._window_state = WindowStatePersistence(window)
    window._window_state.restore()
    app.aboutToQuit.connect(window._window_state.save)

    # MainWindow queues its initial viewport refresh with a zero-delay timer.
    # Do not process Qt events again while the QOpenGLWidget hierarchy is still
    # hidden. Update the splash synchronously, hide it, map the main window, and
    # only then let the normal event loop realize and paint the VTK GL widget.
    startup.set_progress(94, "Finalizing workspace…")
    startup.set_progress(100, "Ready")
    startup.hide()
    window.show()
    startup.deleteLater()
    return app.exec()
