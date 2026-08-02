from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)


class StepDialog(QDialog):
    def __init__(self, step, loads, supports, parent=None, existing_names=()):
        super().__init__(parent)
        self.step = step
        self.existing_names = tuple(existing_names)
        self.setWindowTitle(f"Edit {step.name}")
        self.setMinimumWidth(580)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)
        form = QFormLayout()
        self.name = QLineEdit(step.name)
        form.addRow("Name", self.name)
        self.modes = QSpinBox()
        self.modes.setRange(1, 100000)
        self.modes.setValue(step.number_of_modes)
        if step.step_type in {"Eigenfrequency", "Linear Buckling"}:
            form.addRow("Number of modes", self.modes)
        root.addLayout(form)
        support_group, self.supports = self._checks("Active supports", supports, step.support_refs)
        root.addWidget(support_group)
        self.loads = None
        if step.uses_loads:
            load_group, self.loads = self._checks("Active loads", loads, step.load_refs)
            root.addWidget(load_group)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _accept(self):
        from opencae.model.naming import is_unique
        if not is_unique(self.name.text(), self.existing_names, self.step.name):
            QMessageBox.warning(self, "Duplicate name", f"A step named '{self.name.text().strip()}' already exists.")
            return
        self.accept()

    @staticmethod
    def _checks(title, entities, selected_refs):
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        widget = QListWidget(group)
        layout.addWidget(widget)
        selected_ids = {ref.entity_id for ref in selected_refs}
        for entity in entities:
            item = QListWidgetItem(entity.name)
            item.setData(Qt.ItemDataRole.UserRole, entity.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if entity.id in selected_ids else Qt.CheckState.Unchecked)
            widget.addItem(item)
        return group, widget

    def values(self):
        return {
            "name": self.name.text().strip(),
            "number_of_modes": self.modes.value(),
            "support_ids": self._selected(self.supports),
            "load_ids": self._selected(self.loads) if self.loads else [],
        }

    @staticmethod
    def _selected(widget):
        return [
            widget.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(widget.count())
            if widget.item(index).checkState() == Qt.CheckState.Checked
        ]
