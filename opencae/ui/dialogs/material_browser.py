"""Displays the built-in material library and returns one selected preset."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
)

from opencae.ui.templates import dialog_buttons
from opencae.ui.templates.layouts import dialog_layout


class MaterialBrowserDialog(QDialog):
    """Modal browser for a small set of built-in engineering materials."""

    def __init__(
        self,
        rows,
        pressure_symbol: str,
        density_symbol: str,
        parent=None,
    ):
        """Build the browser from already unit-converted material rows."""
        super().__init__(parent)
        self.setWindowTitle("Material Browser")
        self.setMinimumSize(720, 420)
        self.resize(860, 520)
        root = dialog_layout(self)

        description = QLabel(
            "Choose a starter material. Values are representative "
            "room-temperature engineering data and can be edited after import."
        )
        description.setWordWrap(True)
        root.addWidget(description)

        self.table = QTableWidget(len(rows), 4, self)
        self.table.setMinimumHeight(250)
        self.table.setHorizontalHeaderLabels(
            (
                "Material",
                f"Young's modulus [{pressure_symbol}]",
                "Poisson ratio",
                f"Density [{density_symbol}]",
            )
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)

        for row_index, (name, modulus, poisson, density) in enumerate(rows):
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.ItemDataRole.UserRole, name)
            values = (
                name_item,
                QTableWidgetItem(f"{modulus:.6g}"),
                QTableWidgetItem(f"{poisson:.4g}"),
                QTableWidgetItem(f"{density:.6g}"),
            )
            for column, item in enumerate(values):
                self.table.setItem(row_index, column, item)

        self.table.resizeColumnsToContents()
        if rows:
            self.table.selectRow(0)
        self.table.doubleClicked.connect(self.accept)
        root.addWidget(self.table)

        buttons = dialog_buttons()
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.setText("Add Material")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def selected_preset(self) -> str:
        """Return the selected preset label or an empty string."""
        row = self.table.currentRow()
        if row < 0:
            return ""
        item = self.table.item(row, 0)
        return str(item.data(Qt.ItemDataRole.UserRole) or "") if item else ""
