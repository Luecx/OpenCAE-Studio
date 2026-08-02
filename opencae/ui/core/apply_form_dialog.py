from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QVBoxLayout, QWidget

from .fields import FieldSpec, create_editor, editor_value


class ApplyFormDialog(QDialog):
    apply_requested = pyqtSignal(object)

    def __init__(self, title: str, fields: tuple[FieldSpec, ...], parent: QWidget | None = None, width: int = 520):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(False)
        self.setMinimumWidth(width)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._editors = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(14)
        heading = QLabel(title); heading.setObjectName("PanelTitle"); layout.addWidget(heading)
        form = QFormLayout(); form.setHorizontalSpacing(18); form.setVerticalSpacing(10)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        for spec in fields:
            editor = create_editor(spec); self._editors[spec.key] = editor
            form.addRow(spec.label, editor)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Close,
        )
        apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button is not None: apply_button.setObjectName("PrimaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.close)
        apply_button.clicked.connect(lambda: self.apply_requested.emit(self.values()))
        layout.addWidget(buttons)

    def values(self) -> dict:
        return {key: editor_value(widget) for key, widget in self._editors.items()}
