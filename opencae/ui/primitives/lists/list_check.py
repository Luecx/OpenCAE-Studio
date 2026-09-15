"""Checkable list primitive for named values."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QWidget


class ListCheck(QListWidget):
    def __init__(self, values=(), selected=(), parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("EditorCheckList")
        self.setMinimumHeight(180)
        self.setMinimumWidth(0)
        selected_values = {str(value) for value in selected}
        for value in values:
            label, data = self._option(value)
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, data)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if str(data) in selected_values else Qt.CheckState.Unchecked
            )
            self.addItem(item)

    @staticmethod
    def _option(value) -> tuple[str, object]:
        if hasattr(value, "name") and hasattr(value, "id"):
            return str(value.name), value.id
        if isinstance(value, tuple) and len(value) == 2:
            return str(value[0]), value[1]
        return str(value), value

    def selected_values(self) -> list:
        return [
            self.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(self.count())
            if self.item(index).checkState() == Qt.CheckState.Checked
        ]
