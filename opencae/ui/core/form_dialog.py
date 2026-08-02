from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QFormLayout, QLabel, QVBoxLayout, QWidget

from .controls import dialog_buttons
from .fields import FieldSpec, create_editor, editor_value


class FormDialog(QDialog):
    def __init__(self, title: str, fields: tuple[FieldSpec, ...], parent: QWidget | None = None, width: int = 520):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(width)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._editors = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(14)
        heading = QLabel(title); heading.setObjectName("PanelTitle"); layout.addWidget(heading)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(18); form.setVerticalSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        for spec in fields:
            editor = create_editor(spec)
            self._editors[spec.key] = editor
            form.addRow(spec.label, editor)
        layout.addLayout(form)
        buttons = dialog_buttons(); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict:
        return {key: editor_value(widget) for key, widget in self._editors.items()}
