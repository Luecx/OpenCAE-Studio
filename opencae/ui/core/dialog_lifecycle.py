from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QWidget


def show_modeless_dialog(dialog: QDialog) -> None:
    """Show a top-level dialog and bind deterministic viewport cleanup."""
    _bind_viewport_cleanup(dialog)
    dialog.show()
    activate_dialog(dialog)


def activate_dialog(widget: QWidget | None) -> None:
    if widget is None:
        return
    window = widget if isinstance(widget, QDialog) else widget.window()
    if isinstance(window, QDialog) and window.isWindow():
        window.raise_()
        window.activateWindow()


def _bind_viewport_cleanup(dialog: QDialog) -> None:
    if dialog.property("opencaeViewportCleanupBound"):
        return
    dialog.setProperty("opencaeViewportCleanupBound", True)
    dialog.finished.connect(lambda _code, current=dialog: _cleanup_viewport(current))


def _cleanup_viewport(dialog: QDialog) -> None:
    owner: QWidget | None = dialog
    viewport = None
    while owner is not None:
        viewport = getattr(owner, "viewport", None)
        if viewport is not None:
            break
        owner = owner.parentWidget()
    if viewport is None:
        return
    viewport.cancel_context_pick()
    # Remove only transient picker state. Persistent model-selection and dialog
    # preview channels are managed by their owners and are reapplied here.
    picker = getattr(viewport, "picker", None)
    if picker is not None:
        picker.clear(False)
