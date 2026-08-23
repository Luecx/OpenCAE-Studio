from __future__ import annotations

from PyQt6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget


def read_only_table(
    headers: tuple[str, ...],
    *,
    rows: int = 0,
    show_row_headers: bool = False,
    stretch_columns: tuple[int, ...] = (),
) -> QTableWidget:
    table = QTableWidget(rows, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    table.setAlternatingRowColors(False)
    table.verticalHeader().setVisible(show_row_headers)

    header = table.horizontalHeader()
    for column in range(len(headers)):
        mode = (
            QHeaderView.ResizeMode.Stretch
            if column in stretch_columns
            else QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(column, mode)
    return table
