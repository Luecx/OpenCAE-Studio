"""Run the isolated modern ViewCube visibility test window."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from opencae.ui.core.theme import stylesheet

from .view_cube_test_window import ViewCubeTestWindow


def main() -> int:
    """Start the standalone Qt event loop and return its exit code."""
    application = QApplication(sys.argv)
    application.setApplicationName("OpenCAE ViewCube Test")
    application.setStyleSheet(stylesheet())
    window = ViewCubeTestWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
