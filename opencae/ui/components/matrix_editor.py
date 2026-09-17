from __future__ import annotations

from PyQt6.QtWidgets import QGridLayout, QWidget

from opencae.ui.primitives.inputs.input_matrix_number import InputMatrixNumber
from opencae.ui.primitives.labels.label_matrix_header import LabelMatrixHeader


class MatrixEditor(QWidget):
    def __init__(self, rows: int, columns: int, values=None, parent=None):
        super().__init__(parent)
        self.rows = rows
        self.columns = columns
        self._cells: list[list[InputMatrixNumber]] = []
        data = values or [[0.0] * columns for _ in range(rows)]
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(3)
        layout.setVerticalSpacing(3)
        for column in range(columns):
            layout.addWidget(LabelMatrixHeader(str(column + 1)), 0, column + 1)
        for row in range(rows):
            layout.addWidget(LabelMatrixHeader(str(row + 1)), row + 1, 0)
            current_row = []
            for column in range(columns):
                editor = InputMatrixNumber(float(data[row][column]))
                layout.addWidget(editor, row + 1, column + 1)
                current_row.append(editor)
            self._cells.append(current_row)

    def values(self) -> list[list[float]]:
        return [[cell.value() for cell in row] for row in self._cells]
