"""One labelled numeric component with optional activation checkbox and unit."""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from opencae.ui.foundation.metrics import FIELD_LABEL_SPACING
from opencae.ui.primitives.checks import CheckForm
from opencae.ui.primitives.labels import LabelForm
from .control_numeric_unit import ControlNumericUnit


class ControlComponentNumber(QWidget):
    def __init__(
        self,
        label: str,
        value=None,
        *,
        unit: str = "",
        checkable: bool = False,
        editable: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._check = CheckForm(str(label), checked=value is not None) if checkable else None
        self._label = None if checkable else LabelForm(str(label))
        self.editor = ControlNumericUnit(float(value or 0.0), unit, decimals=12)
        self._editable = bool(editable)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(FIELD_LABEL_SPACING)
        layout.addWidget(self._check or self._label)
        layout.addWidget(self.editor)
        if self._check is not None:
            self._check.toggled.connect(self._sync_enabled)
        self._sync_enabled()

    def _sync_enabled(self, *_args) -> None:
        active = self._check is None or self._check.isChecked()
        self.editor.setEnabled(self._editable and active)

    def value(self):
        if self._check is not None and not self._check.isChecked():
            return None
        return self.editor.value()

    def set_value(self, value) -> None:
        if self._check is not None:
            self._check.setChecked(value is not None)
        self.editor.setValue(float(value or 0.0))
        self._sync_enabled()
