"""Provides interpolation-order and formulation controls for element conversion."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QHBoxLayout, QVBoxLayout, QWidget

from opencae.model.element_catalog import formulations, resulting_type
from opencae.model.entities.mesh import ElementOrder
from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.templates import (
    FieldLabel,
    ReadOnlyValue,
    apply_primary_control_height,
    field_block,
    field_row,
)


class ElementOrderPanel(QWidget):
    """Choose one definite interpolation order and optional formulation override."""

    changed = pyqtSignal()

    def __init__(self, parent=None):
        """Build order toggles plus canonical formulation/result fields."""
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        order_row = QHBoxLayout()
        order_row.setContentsMargins(0, 0, 0, 0)
        order_row.setSpacing(18)
        self.first = QCheckBox("First Order")
        self.second = QCheckBox("Second Order")
        for button in (self.first, self.second):
            button.setTristate(True)
            order_row.addWidget(button)
        order_row.addStretch(1)
        root.addLayout(order_row)

        self.mixed = FieldLabel("")
        root.addWidget(self.mixed)

        self.formulation = ChevronComboBox()
        self.formulation.setMinimumWidth(0)
        apply_primary_control_height(self.formulation)
        self.result = ReadOnlyValue("—")
        root.addWidget(
            field_row(
                field_block("Formulation", self.formulation),
                field_block("Resulting type", self.result),
            )
        )

        self.first.clicked.connect(lambda: self._choose(ElementOrder.FIRST))
        self.second.clicked.connect(lambda: self._choose(ElementOrder.SECOND))
        self.formulation.currentTextChanged.connect(self._update_result)
        self.key = None

    def set_summary(self, summary):
        """Reflect topology statistics and available formulations in the panel."""
        self.key = summary.key if summary else None
        if not summary:
            self.first.setCheckState(Qt.CheckState.Unchecked)
            self.second.setCheckState(Qt.CheckState.Unchecked)
            self.mixed.clear()
            self.formulation.blockSignals(True)
            self.formulation.clear()
            self.formulation.blockSignals(False)
            self.result.set_value("—")
            return
        mixed = bool(summary.first and summary.second)
        self.first.setCheckState(
            Qt.CheckState.PartiallyChecked
            if mixed
            else Qt.CheckState.Checked if summary.first else Qt.CheckState.Unchecked
        )
        self.second.setCheckState(
            Qt.CheckState.PartiallyChecked
            if mixed
            else Qt.CheckState.Checked if summary.second else Qt.CheckState.Unchecked
        )
        self.mixed.setText(
            f"Mixed order: {summary.first:,} first-order / {summary.second:,} second-order"
            if mixed
            else ""
        )
        self.formulation.blockSignals(True)
        self.formulation.clear()
        self.formulation.addItem("Keep Existing")
        choices = formulations(summary.key)
        self.formulation.addItems(choices)
        current = next(iter(summary.formulations)) if len(summary.formulations) == 1 else "Keep Existing"
        self.formulation.setCurrentText(current if current in choices else "Keep Existing")
        self.formulation.blockSignals(False)
        self._update_result()

    def choose(self, order):
        """Select an interpolation order programmatically."""
        self._choose(ElementOrder(order))

    def set_formulation(self, value):
        """Select a formulation by its visible catalog name when available."""
        index = self.formulation.findText(str(value))
        if index >= 0:
            self.formulation.setCurrentIndex(index)

    def _choose(self, order):
        """Make the two order checkboxes behave as an explicit exclusive choice."""
        self.first.setCheckState(
            Qt.CheckState.Checked if order == ElementOrder.FIRST else Qt.CheckState.Unchecked
        )
        self.second.setCheckState(
            Qt.CheckState.Checked if order == ElementOrder.SECOND else Qt.CheckState.Unchecked
        )
        self.mixed.clear()
        self._update_result()
        self.changed.emit()

    def order(self):
        """Return the definite selected order, or None while the state is mixed."""
        if self.first.checkState() == Qt.CheckState.Checked:
            return ElementOrder.FIRST
        if self.second.checkState() == Qt.CheckState.Checked:
            return ElementOrder.SECOND
        return None

    def _update_result(self, *_):
        """Display the element type produced by the current order/formulation pair."""
        formulation = self.formulation.currentText()
        text = (
            "Preserve current formulations"
            if not self.key or formulation == "Keep Existing" or not self.order()
            else resulting_type(self.key, self.order(), formulation)
        )
        self.result.set_value(text)
        self.changed.emit()
