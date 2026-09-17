from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem

from opencae.units import QUANTITIES
from opencae.units.formatting import conversion_text


class UnitSystemTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(0, 3, parent); self.setHorizontalHeaderLabels(("Quantity", "Unit", "To current system"))
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.verticalHeader().hide(); self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents); self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

    def refresh(self, source, target):
        self.setRowCount(len(QUANTITIES))
        for row, quantity in enumerate(QUANTITIES):
            scale, offset = source.conversion_to(target, quantity)
            values = (quantity.label, source.symbol(quantity), conversion_text(scale, offset))
            for column, value in enumerate(values):
                item = QTableWidgetItem(value); item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | (Qt.AlignmentFlag.AlignRight if column else Qt.AlignmentFlag.AlignLeft)); self.setItem(row, column, item)
