from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject, QTimer, Qt
from PyQt6.QtWidgets import QDialog, QFormLayout, QStackedWidget, QWidget


_FORM_HORIZONTAL_SPACING = 18
_FORM_VERTICAL_SPACING = 10
_NATURAL_LABEL_WIDTH = "_opencae_natural_form_label_width"
_POLISH_PENDING = "_opencae_form_polish_pending"


class DialogFormPolisher(QObject):
    """Keep form geometry consistent across every layout inside a dialog.

    Qt sizes the label column of each ``QFormLayout`` independently.  This is
    particularly visible in OpenCAE dialogs where a selector lives in one form
    and the selector-specific options live in another form inside a
    ``QStackedWidget``: the fields start at different x positions even though
    they visually belong to one form.

    The application-level event filter schedules a polish both when a dialog is
    shown and whenever one of its child widgets requests a new layout.  The
    latter is important for forms rebuilt after changing a type/method combo.
    """

    def eventFilter(self, watched, event):
        event_type = event.type()
        if event_type == QEvent.Type.Show and isinstance(watched, QDialog):
            self._schedule(watched)
        elif event_type == QEvent.Type.LayoutRequest and isinstance(watched, QWidget):
            try:
                window = watched.window()
            except RuntimeError:
                window = None
            if isinstance(window, QDialog) and window.isVisible():
                self._schedule(window)
        return False

    @staticmethod
    def _schedule(dialog: QDialog) -> None:
        try:
            if bool(dialog.property(_POLISH_PENDING)):
                return
            dialog.setProperty(_POLISH_PENDING, True)
        except RuntimeError:
            return

        def apply():
            try:
                dialog.setProperty(_POLISH_PENDING, False)
                polish_dialog_forms(dialog)
            except RuntimeError:
                # The dialog may have been WA_DeleteOnClose'd before the queued
                # polish runs.
                return

        QTimer.singleShot(0, apply)


def polish_dialog_forms(dialog: QDialog) -> None:
    """Normalize nested forms and give them one shared label-column width."""
    top_layout = dialog.layout()

    # Stacked pages are implementation detail, not an additional visual inset.
    # Their outer container already supplies the dialog padding.
    for stack in dialog.findChildren(QStackedWidget):
        for index in range(stack.count()):
            page = stack.widget(index)
            layout = page.layout() if page is not None else None
            if layout is not None:
                layout.setContentsMargins(0, 0, 0, 0)

    forms = tuple(dialog.findChildren(QFormLayout))
    labels = []

    for form in forms:
        # A form used directly as the dialog's root layout owns the outer
        # padding. Nested forms must not add another inset.
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

        for row in range(form.rowCount()):
            item = form.itemAt(row, QFormLayout.ItemRole.LabelRole)
            widget = item.widget() if item is not None else None
            if widget is None:
                continue
            if widget.property(_NATURAL_LABEL_WIDTH) is None:
                widget.setProperty(
                    _NATURAL_LABEL_WIDTH,
                    max(widget.minimumWidth(), widget.sizeHint().width()),
                )
            labels.append(widget)

    if not labels:
        return

    # This is the key part: QFormLayout has no API for sharing its label column
    # with another QFormLayout, so make every label reserve the width of the
    # widest label in this dialog.  All field columns then start at exactly the
    # same x coordinate, including forms on hidden/dynamic stack pages.
    label_width = max(
        int(widget.property(_NATURAL_LABEL_WIDTH) or 0)
        for widget in labels
    )
    for widget in labels:
        if widget.minimumWidth() != label_width:
            widget.setMinimumWidth(label_width)
