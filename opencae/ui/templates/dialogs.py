from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QVBoxLayout

from .layouts import dialog_layout, form_layout
from .primitives import label
from .specs import LabelRole


@dataclass(slots=True)
class DialogScaffold:
    root: QVBoxLayout
    form: QFormLayout


def scaffold_dialog(
    dialog: QDialog,
    title: str,
    *,
    width: int = 520,
    modal: bool = True,
    delete_on_close: bool = False,
) -> DialogScaffold:
    dialog.setWindowTitle(title)
    dialog.setModal(modal)
    dialog.setMinimumWidth(width)
    dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
    if delete_on_close:
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

    root = dialog_layout(dialog)
    root.addWidget(label(title, role=LabelRole.TITLE))
    form = form_layout()
    root.addLayout(form)
    return DialogScaffold(root, form)


def dialog_buttons(
    *,
    include_apply: bool = False,
    close_instead_of_cancel: bool = False,
    primary_apply: bool = False,
) -> QDialogButtonBox:
    cancel = (
        QDialogButtonBox.StandardButton.Close
        if close_instead_of_cancel
        else QDialogButtonBox.StandardButton.Cancel
    )
    flags = QDialogButtonBox.StandardButton.Ok | cancel
    if include_apply:
        flags |= QDialogButtonBox.StandardButton.Apply
    buttons = QDialogButtonBox(flags)

    primary = (
        buttons.button(QDialogButtonBox.StandardButton.Apply)
        if primary_apply and include_apply
        else buttons.button(QDialogButtonBox.StandardButton.Ok)
    )
    if primary is not None:
        primary.setObjectName("PrimaryButton")
    return buttons


def apply_close_buttons() -> QDialogButtonBox:
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Apply
        | QDialogButtonBox.StandardButton.Close
    )
    apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
    if apply_button is not None:
        apply_button.setObjectName("PrimaryButton")
    return buttons
