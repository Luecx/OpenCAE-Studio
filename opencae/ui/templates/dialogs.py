"""Builds standardized dialog shells and button boxes for OpenCAE UI forms."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

from .field_stack import FieldStack
from .layouts import dialog_layout


# Editor dialogs routinely contain full-width selectors, paths and technical
# labels. Give those controls enough horizontal room on ordinary desktop
# displays; truly compact dialogs can still opt into a smaller explicit width.
DEFAULT_DIALOG_WIDTH = 720


@dataclass(slots=True)
class DialogScaffold:
    """References the reusable root and semantic field stack for one dialog."""

    root: QVBoxLayout
    form: FieldStack


def scaffold_dialog(
    dialog: QDialog,
    title: str,
    *,
    width: int = DEFAULT_DIALOG_WIDTH,
    modal: bool = True,
    delete_on_close: bool = False,
) -> DialogScaffold:
    """Configure a dialog with the canonical label-above editor scaffold."""
    dialog.setWindowTitle(title)
    dialog.setModal(modal)
    dialog.setMinimumWidth(width)
    dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
    if delete_on_close:
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

    root = dialog_layout(dialog)
    form = FieldStack()
    root.addWidget(form)
    return DialogScaffold(root, form)


def dialog_buttons(
    *,
    include_apply: bool = False,
    close_instead_of_cancel: bool = False,
    primary_apply: bool = False,
) -> QDialogButtonBox:
    """Create the canonical OK/Cancel-or-Close dialog button box."""
    cancel = (
        QDialogButtonBox.StandardButton.Close
        if close_instead_of_cancel
        else QDialogButtonBox.StandardButton.Cancel
    )
    flags = QDialogButtonBox.StandardButton.Ok | cancel
    if include_apply:
        flags |= QDialogButtonBox.StandardButton.Apply
    buttons = QDialogButtonBox(flags)

    # Styling the logical primary action here prevents every dialog from having
    # to know stylesheet object names.
    primary = (
        buttons.button(QDialogButtonBox.StandardButton.Apply)
        if primary_apply and include_apply
        else buttons.button(QDialogButtonBox.StandardButton.Ok)
    )
    if primary is not None:
        primary.setObjectName("PrimaryButton")
    return buttons


def apply_close_buttons() -> QDialogButtonBox:
    """Create the canonical non-modal Apply/Close button box."""
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Apply
        | QDialogButtonBox.StandardButton.Close
    )
    apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
    if apply_button is not None:
        apply_button.setObjectName("PrimaryButton")
    return buttons
