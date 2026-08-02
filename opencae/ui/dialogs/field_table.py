from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget


class FieldTable(QWidget):
    def __init__(self, components=1, rows=None, parent=None):
        super().__init__(parent); self.components = components
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(); layout.addWidget(self.table, 1)
        row = QHBoxLayout(); add = QPushButton("Add row"); remove = QPushButton("Remove row")
        add.clicked.connect(self.add_row); remove.clicked.connect(self.remove_row)
        row.addWidget(add); row.addWidget(remove); row.addStretch(1); layout.addLayout(row)
        self.set_components(components)
        for values in rows or (): self.add_row(values)
        if not rows:
            for _ in range(6): self.add_row()

    def set_components(self, count):
        self.components = max(1, int(count)); old = self.values() if self.table.columnCount() else []
        self.table.setColumnCount(self.components + 1)
        self.table.setHorizontalHeaderLabels(["ID", *[f"C{i + 1}" for i in range(self.components)]])
        self.table.horizontalHeader().setStretchLastSection(True)
        if old:
            self.table.setRowCount(0)
            for values in old: self.add_row(values)

    def add_row(self, values=None):
        row = self.table.rowCount(); self.table.insertRow(row); values = values or ()
        for col in range(self.table.columnCount()):
            self.table.setItem(row, col, QTableWidgetItem(str(values[col]) if col < len(values) else ""))

    def remove_row(self):
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        for row in rows: self.table.removeRow(row)

    def values(self):
        result = []
        for row in range(self.table.rowCount()):
            values = [self.table.item(row, col).text().strip() if self.table.item(row, col) else "" for col in range(self.table.columnCount())]
            if any(values): result.append(values)
        return result
