"""Provides one labelled numeric component with optional enable checkbox and unit."""

from __future__ import annotations

from PyQt6.QtWidgets import QCheckBox, QVBoxLayout, QWidget

from .control_metrics import FIELD_LABEL_SPACING
from .field_label import FieldLabel
from .numeric_unit_input import NumericUnitInput


class ComponentField(QWidget):
    """Edit one vector component using the canonical label-above-control geometry."""

    def __init__(
        self,
        label: str,
        value=None,
        *,
        unit: str = "",
        checkable: bool = False,
        editable: bool = True,
        parent=None,
    ):
        """Build one component while keeping optional activation separate from its value."""
        super().__init__(parent)
        self._check = QCheckBox(str(label)) if checkable else None
        self._label = None if checkable else FieldLabel(str(label))
        self.editor = NumericUnitInput(float(value or 0.0), unit, decimals=12)
        self._editable = bool(editable)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(FIELD_LABEL_SPACING)
        layout.addWidget(self._check or self._label)
        layout.addWidget(self.editor)

        if self._check is not None:
            self._check.setChecked(value is not None)
            self._check.toggled.connect(self._sync_enabled)
        self._sync_enabled()

    def _sync_enabled(self, *_args) -> None:
        """Enable numeric editing only when the component is active and editable."""
        active = self._check is None or self._check.isChecked()
        self.editor.setEnabled(self._editable and active)

    def value(self):
        """Return the numeric value or None when an optional component is inactive."""
        if self._check is not None and not self._check.isChecked():
            return None
        return self.editor.value()

    def set_value(self, value) -> None:
        """Replace the value and activation state represented by this component."""
        if self._check is not None:
            self._check.setChecked(value is not None)
        self.editor.setValue(float(value or 0.0))
        self._sync_enabled()
