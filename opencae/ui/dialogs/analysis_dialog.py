"""Edits an Analysis and its ordered references to shared project steps."""

from __future__ import annotations

from copy import deepcopy

from PyQt6.QtWidgets import QMessageBox

from opencae.model.core import EntityRef
from opencae.ui.core.named_entity_dialog import NamedEntityDialog
from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.templates import CheckList, SectionHeading, apply_primary_control_height


class AnalysisDialog(NamedEntityDialog):
    """Create or edit an analysis without owning or duplicating its steps."""

    def __init__(
        self,
        value,
        steps,
        solvers,
        *,
        existing_names=(),
        parent=None,
    ):
        """Build solver selection and one checked list of referenced shared steps."""
        super().__init__(
            "Analysis",
            value,
            existing_names=existing_names,
            parent=parent,
            width=620,
        )
        self._steps = tuple(steps)
        selected = {ref.entity_id for ref in value.step_refs}

        self.solver = ChevronComboBox()
        self.solver.setMinimumWidth(0)
        for solver in tuple(solvers or ("FEMaster",)):
            self.solver.addItem(str(solver), str(solver))
        index = self.solver.findData(value.solver)
        self.solver.setCurrentIndex(max(index, 0))
        apply_primary_control_height(self.solver)
        self.form.addRow("Solver", self.solver)

        self.add_widget(SectionHeading("Referenced Steps"))
        step_options = [
            (f"{step.name}  [{step.step_type}]", step.id)
            for step in self._steps
        ]
        self.step_list = CheckList(step_options, selected)
        self.step_list.setMinimumHeight(240)
        self.add_widget(self.step_list)
        self.finish()

    def result(self):
        """Return a detached Analysis candidate referencing checked shared steps in order."""
        candidate = self.apply_name(deepcopy(self.value))
        candidate.solver = str(self.solver.currentData() or "FEMaster")
        candidate.step_refs = [
            EntityRef(str(step_id), "AnalysisStep")
            for step_id in self.step_list.selected_values()
        ]
        candidate.steps = []
        return candidate

    def validate(self) -> bool:
        """Require valid naming and at least one referenced shared analysis step."""
        if not super().validate():
            return False
        if not self.step_list.selected_values():
            QMessageBox.warning(
                self,
                "Missing steps",
                "Select at least one shared step for this analysis.",
            )
            return False
        return True
