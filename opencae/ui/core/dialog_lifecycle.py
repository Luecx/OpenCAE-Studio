from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QWidget


def show_modeless_dialog(dialog: QDialog) -> None:
    """Show and activate only an actual top-level dialog.

    Calling ``raise_``/``activateWindow`` on dock descendants causes Qt's
    ``must be a top level window`` warnings and can destabilize nested editors.
    """
    dialog.show()
    activate_dialog(dialog)


def activate_dialog(widget: QWidget | None) -> None:
    if widget is None:
        return
    window = widget if isinstance(widget, QDialog) else widget.window()
    if isinstance(window, QDialog) and window.isWindow():
        window.raise_()
        window.activateWindow()
