from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout

from opencae.model.core import EntityRef


class StepCollectorsDialog(QDialog):
    def __init__(self, steps, loads, supports, parent=None):
        super().__init__(parent)
        self.steps = steps
        self.loads = loads
        self.supports = supports
        self.setWindowTitle("Step Load / Support Matrix")
        self.resize(920, 560)
        root = QVBoxLayout(self)
        root.addWidget(QLabel("Check which collectors are active in each step."))
        self.table = QTableWidget(len(supports) + len(loads), len(steps) + 1)
        self.table.setHorizontalHeaderLabels(("Collector", *[step.name for step in steps]))
        rows = [("Support", entity) for entity in supports] + [("Load", entity) for entity in loads]
        for row, (kind, entity) in enumerate(rows):
            item = QTableWidgetItem(f"{kind}: {entity.name}")
            item.setData(Qt.ItemDataRole.UserRole, entity.id)
            self.table.setItem(row, 0, item)
            for col, step in enumerate(steps, 1):
                self._cell(row, col, kind, entity.id, step)
        self.table.resizeColumnsToContents()
        root.addWidget(self.table, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _cell(self, row, col, kind, entity_id, step):
        item = QTableWidgetItem()
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        enabled = kind == "Support" or step.uses_loads
        if not enabled:
            item.setFlags(Qt.ItemFlag.NoItemFlags)
        refs = step.support_refs if kind == "Support" else step.load_refs
        selected = entity_id in {ref.entity_id for ref in refs}
        item.setCheckState(Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked)
        self.table.setItem(row, col, item)

    def values(self):
        result = {}
        for col, step in enumerate(self.steps, 1):
            support_ids = [
                entity.id
                for row, entity in enumerate(self.supports)
                if self._checked(row, col)
            ]
            offset = len(self.supports)
            load_ids = [
                entity.id
                for index, entity in enumerate(self.loads)
                if step.uses_loads and self._checked(offset + index, col)
            ]
            result[step.id] = {"support_ids": support_ids, "load_ids": load_ids}
        return result

    def apply(self):
        """Legacy convenience method; new controllers consume :meth:`values`."""
        values = self.values()
        for step in self.steps:
            selected = values[step.id]
            step.support_refs = [EntityRef(entity_id, "Support") for entity_id in selected["support_ids"]]
            step.load_refs = [EntityRef(entity_id, "Load") for entity_id in selected["load_ids"]]

    def _checked(self, row, col):
        item = self.table.item(row, col)
        return item is not None and item.checkState() == Qt.CheckState.Checked
