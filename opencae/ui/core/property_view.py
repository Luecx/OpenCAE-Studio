from __future__ import annotations

from dataclasses import asdict, is_dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .theme import PALETTE


class PropertyView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PropertiesPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        self.title = QLabel("No selection")
        self.title.setObjectName("PanelTitle")
        layout.addWidget(self.title)
        self.type_label = QLabel("Select an object in the project tree")
        self.type_label.setObjectName("MutedLabel")
        layout.addWidget(self.type_label)
        self.table = QTableWidget(0, 2)
        self.table.horizontalHeader().hide()
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 132)
        layout.addWidget(self.table, 1)

    def show_object(self, obj: object | None) -> None:
        title, type_name, data = self._object_data(obj)
        self.title.setText(title)
        self.type_label.setText(type_name)
        rows = []
        for key, value in data.items():
            if key in {"name", "geometry_backed"}:
                continue
            if isinstance(value, (list, dict, tuple)):
                value = self._summarize(value)
            rows.append((key.replace("_", " ").title(), str(value)))
        self.table.setRowCount(len(rows))
        for row, (key, value) in enumerate(rows):
            key_item = QTableWidgetItem(key)
            key_item.setForeground(QColor(PALETTE["muted"]))
            value_item = QTableWidgetItem(value)
            key_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 0, key_item)
            self.table.setItem(row, 1, value_item)
            self.table.setRowHeight(row, 28)

    @staticmethod
    def _summarize(value) -> str:
        if isinstance(value, dict):
            return f"{len(value)} entries"
        if isinstance(value, (list, tuple)):
            return f"{len(value)} items"
        return str(value)

    @staticmethod
    def _object_data(obj):
        if obj is None:
            return "No selection", "Select an object in the project tree", {}
        if is_dataclass(obj):
            data = asdict(obj)
        elif isinstance(obj, dict):
            data = obj
        else:
            data = {"value": str(obj)}
        title = str(data.get("name", type(obj).__name__))
        return title, type(obj).__name__.replace("_", " "), data
