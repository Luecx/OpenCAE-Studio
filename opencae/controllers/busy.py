from __future__ import annotations

from contextlib import contextmanager

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication


@contextmanager
def busy_cursor():
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        yield
    finally:
        QApplication.restoreOverrideCursor()
