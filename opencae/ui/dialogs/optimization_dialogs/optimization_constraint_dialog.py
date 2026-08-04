"""Edits one scalar volume or mass resource constraint for topology optimization."""

from copy import deepcopy

from PyQt6.QtWidgets import QCheckBox, QLabel, QMessageBox

from opencae.model.core import EntityRef
from opencae.model.entities.optimization import (
    ConstraintOperator,
    OptimizationConstraint,
    ResponseType,
)
from opencae.ui.core.fields import FieldSpec, create_editor, editor_value
from opencae.ui.core.named_entity_dialog import NamedEntityDialog
from opencae.ui.core.widgets import ChevronComboBox, ReferenceSelector

_RESOURCE_TYPES = {
    ResponseType.VOLUME,
    ResponseType.VOLUME_FRACTION,
    ResponseType.MASS,
    ResponseType.MASS_FRACTION,
}


class OptimizationConstraintDialog(NamedEntityDialog):
    """Create or edit the resource response limit consumed by OC+bisection."""

    def __init__(
        self,
        optimization,
        value=None,
        *,
        existing_names=(),
        parent=None,
    ):
        entity = value or OptimizationConstraint(name="Constraint-1")
        super().__init__(
            "Optimization Constraint",
            entity,
            existing_names=existing_names,
            parent=parent,
            width=540,
        )
        responses = [
            (item.name, item.id)
            for item in optimization.responses
            if item.response_type in _RESOURCE_TYPES
        ]
        self.response = ReferenceSelector(
            responses,
            self.value.response_ref.entity_id,
        )
        self.operator = ChevronComboBox()
        self.operator.addItem(
            ConstraintOperator.LESS_EQUAL.value,
            ConstraintOperator.LESS_EQUAL.value,
        )
        self.limit = create_editor(
            FieldSpec(
                "limit",
                "Limit",
                kind="float",
                default=float(self.value.limit),
                minimum=1.0e-12,
                maximum=1.0e30,
                decimals=9,
            )
        )
        self.active = QCheckBox("Enabled")
        self.active.setChecked(self.value.active)

        self.form.addRow("Response", self.response)
        self.form.addRow("Operator", self.operator)
        self.form.addRow("Limit", self.limit)
        self.form.addRow("", self.active)

        note = QLabel(
            "OC + bisection currently supports exactly one enabled <= resource constraint."
        )
        note.setWordWrap(True)
        note.setObjectName("MutedLabel")
        self.add_widget(note)
        self.finish()

    def result(self):
        candidate = self.apply_name(deepcopy(self.value))
        candidate.response_ref = EntityRef(
            str(self.response.currentValue() or ""),
            "OptimizationResponse",
        )
        candidate.operator = ConstraintOperator(self.operator.currentData())
        candidate.limit = float(editor_value(self.limit))
        candidate.active = self.active.isChecked()
        return candidate

    def validate(self) -> bool:
        if not super().validate():
            return False
        if not self.response.currentValue():
            QMessageBox.warning(
                self,
                "Missing constraint response",
                "Create and select a volume or mass response first.",
            )
            return False
        return True
