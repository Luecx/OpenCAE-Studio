from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFormLayout, QLabel, QVBoxLayout, QWidget

from .apply_dialog import ApplyDialog
from .controls import dialog_buttons
from .fields import FieldSpec, create_editor, editor_value
from .unit_context import unit_system_for


class FormDialog(ApplyDialog):
    def __init__(self, title: str, fields: tuple[FieldSpec, ...], parent: QWidget | None = None, width: int = 520, allow_apply: bool = False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(width)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._editors = {}
        unit_system = unit_system_for(self)
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
            editor = create_editor(spec, unit_system)
            self._editors[spec.key] = editor
            form.addRow(spec.label, editor)
        layout.addLayout(form)
        buttons = dialog_buttons(include_apply=allow_apply); self.bind_buttons(buttons, allow_apply)
        layout.addWidget(buttons)

    def values(self) -> dict:
        return {key: editor_value(widget) for key, widget in self._editors.items()}
