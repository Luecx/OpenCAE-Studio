"""Edits the stiffness-energy response selected as topology objective."""

from copy import deepcopy

from PyQt6.QtWidgets import QLabel, QMessageBox

from opencae.model.core import EntityRef
from opencae.model.entities.optimization import (
    OptimizationObjective,
    ResponseType,
)
from opencae.ui.core.named_entity_dialog import NamedEntityDialog
from opencae.ui.core.widgets import ReferenceSelector


class OptimizationObjectiveDialog(NamedEntityDialog):
    """Create or edit the single minimize objective of a topology setup."""

    def __init__(
        self,
        optimization,
        value=None,
        *,
        existing_names=(),
        parent=None,
    ):
        entity = value or OptimizationObjective(
            name="Minimize Stiffness Energy"
        )
        super().__init__(
            "Optimization Objective",
            entity,
            existing_names=existing_names,
            parent=parent,
            width=520,
        )
        responses = [
            (item.name, item.id)
            for item in optimization.responses
            if item.response_type == ResponseType.STIFFNESS_ENERGY
        ]
        self.response = ReferenceSelector(
            responses,
            self.value.response_ref.entity_id,
        )
        self.form.addRow("Response", self.response)
        self.form.addRow("Sense", QLabel("Minimize"))
        self.finish()

    def result(self):
        candidate = self.apply_name(deepcopy(self.value))
        candidate.response_ref = EntityRef(
            str(self.response.currentValue() or ""),
            "OptimizationResponse",
        )
        candidate.sense = "minimize"
        return candidate

    def validate(self) -> bool:
        if not super().validate():
            return False
        if not self.response.currentValue():
            QMessageBox.warning(
                self,
                "Missing objective response",
                "Create and select a Stiffness Energy response first.",
            )
            return False
        return True
