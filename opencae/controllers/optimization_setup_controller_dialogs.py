"""Owns modeless dialog lifecycle for topology Study setup workflows."""

from __future__ import annotations

from PyQt6.QtWidgets import QMessageBox

from opencae.ui.core.dialog_lifecycle import show_modeless_dialog


def show_setup_dialog(controller, dialog, accepted) -> None:
    """Show one setup dialog and route its accepted state through validation."""
    controller._dialogs.append(dialog)

    def apply() -> None:
        """Validate, persist, and close one setup dialog submission."""
        if hasattr(dialog, "validate") and not dialog.validate():
            return
        try:
            accepted()
        except Exception as exc:
            QMessageBox.warning(dialog, "Study definition", str(exc))
            return
        dialog.close()

    # Dialog classes own their standard buttons, but the controller owns the
    # persistence transaction performed on acceptance.
    try:
        dialog.buttons.accepted.disconnect()
    except (TypeError, RuntimeError):
        pass
    dialog.buttons.accepted.connect(apply)
    dialog.finished.connect(
        lambda _code, value=dialog: setup_dialog_closed(controller, value)
    )
    show_modeless_dialog(dialog)


def setup_dialog_closed(controller, dialog) -> None:
    """Release topology picking/preview state when a setup dialog closes."""
    if dialog in controller._dialogs:
        controller._dialogs.remove(dialog)
    controller.parent.viewport.cancel_context_pick()
    controller.parent.viewport.clear_datum_reference_preview()
