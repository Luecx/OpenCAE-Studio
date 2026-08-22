"""Edits an Analysis and its ordered references to shared project steps."""

from copy import deepcopy

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QMessageBox

from opencae.model.core import EntityRef
from opencae.ui.core.named_entity_dialog import NamedEntityDialog
from opencae.ui.core.widgets import ChevronComboBox


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
        super().__init__(
            "Analysis",
            value,
            existing_names=existing_names,
            parent=parent,
            width=560,
        )
        self._steps = tuple(steps)
        selected = {ref.entity_id for ref in value.step_refs}

        self.solver = ChevronComboBox()
        for solver in tuple(solvers or ("FEMaster",)):
            self.solver.addItem(str(solver), str(solver))
        index = self.solver.findData(value.solver)
        self.solver.setCurrentIndex(max(index, 0))
        self.form.addRow("Solver", self.solver)

        self.step_list = QListWidget()
        self.step_list.setAlternatingRowColors(True)
        self.step_list.setMinimumHeight(220)
        for step in self._steps:
            item = QListWidgetItem(f"{step.name}  [{step.step_type}]")
            item.setData(Qt.ItemDataRole.UserRole, step.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked
                if step.id in selected
                else Qt.CheckState.Unchecked
            )
            self.step_list.addItem(item)
        self.add_widget(QLabel("Referenced steps, in project order"))
        self.add_widget(self.step_list)
        self.finish()

    def result(self):
        candidate = self.apply_name(deepcopy(self.value))
        candidate.solver = str(self.solver.currentData() or "FEMaster")
        candidate.step_refs = [
            EntityRef(
                str(self.step_list.item(row).data(Qt.ItemDataRole.UserRole)),
                "AnalysisStep",
            )
            for row in range(self.step_list.count())
            if self.step_list.item(row).checkState() == Qt.CheckState.Checked
        ]
        candidate.steps = []
        return candidate

    def validate(self) -> bool:
        if not super().validate():
            return False
        if not any(
            self.step_list.item(row).checkState() == Qt.CheckState.Checked
            for row in range(self.step_list.count())
        ):
            QMessageBox.warning(
                self,
                "Missing steps",
                "Select at least one shared step for this analysis.",
            )
            return False
        return True
