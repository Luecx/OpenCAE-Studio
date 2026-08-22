from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtWidgets import QDialog, QFormLayout, QStackedWidget


_FORM_HORIZONTAL_SPACING = 18
_FORM_VERTICAL_SPACING = 10


class DialogFormPolisher(QObject):
    """Apply one form-layout geometry standard to every application dialog.

    Many OpenCAE dialogs contain a selector followed by a QStackedWidget whose
    pages use their own QFormLayout. Qt gives those child layouts their own
    default margins, which makes labels jump to the right and makes the fields
    end before the selector above. Polishing the dialog when it is shown keeps
    every form block on the same outer left/right edges without changing the
    intentional margins of the dialog itself.
    """

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Show and isinstance(watched, QDialog):
            polish_dialog_forms(watched)
        return False


def polish_dialog_forms(dialog: QDialog) -> None:
    """Normalize forms and stacked-page margins inside one dialog."""
    top_layout = dialog.layout()

    for stack in dialog.findChildren(QStackedWidget):
        for index in range(stack.count()):
            page = stack.widget(index)
            layout = page.layout() if page is not None else None
            if layout is not None:
                layout.setContentsMargins(0, 0, 0, 0)

    for form in dialog.findChildren(QFormLayout):
        # A form used directly as the dialog's root layout owns the dialog's
        # outer padding. Nested forms do not: their parent/root already supplies
        # that padding and an additional margin is what causes the misalignment.
        if form is not top_layout:
            form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(_FORM_HORIZONTAL_SPACING)
        form.setVerticalSpacing(_FORM_VERTICAL_SPACING)
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
