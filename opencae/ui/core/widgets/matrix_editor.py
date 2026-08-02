from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractSpinBox, QDoubleSpinBox, QGridLayout, QLabel, QWidget


class MatrixEditor(QWidget):
    def __init__(self, rows: int, columns: int, values=None, parent=None):
        super().__init__(parent)
        self.rows = rows
        self.columns = columns
        self._cells: list[list[QDoubleSpinBox]] = []
        data = values or [[0.0] * columns for _ in range(rows)]
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(3)
        layout.setVerticalSpacing(3)
        for column in range(columns):
            header = QLabel(str(column + 1))
            header.setObjectName("MatrixHeader")
            header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(header, 0, column + 1)
        for row in range(rows):
            header = QLabel(str(row + 1))
            header.setObjectName("MatrixHeader")
            header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(header, row + 1, 0)
            current_row = []
            for column in range(columns):
                editor = QDoubleSpinBox()
                editor.setObjectName("MatrixCell")
                editor.setRange(-1.0e30, 1.0e30)
                editor.setDecimals(8)
                editor.setValue(float(data[row][column]))
                editor.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
                editor.setMinimumWidth(76)
                editor.setAlignment(Qt.AlignmentFlag.AlignRight)
                layout.addWidget(editor, row + 1, column + 1)
                current_row.append(editor)
            self._cells.append(current_row)

    def values(self) -> list[list[float]]:
        return [[cell.value() for cell in row] for row in self._cells]
