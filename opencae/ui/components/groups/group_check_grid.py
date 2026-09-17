"""Compact grid composed from form checkbox primitives."""

from __future__ import annotations

from PyQt6.QtWidgets import QGridLayout, QWidget

from opencae.ui.primitives.checks import CheckForm


class GroupCheckGrid(QWidget):
    def __init__(self, labels, values=None, *, columns: int = 3, parent=None) -> None:
        super().__init__(parent)
        self._checks: list[CheckForm] = []
        labels = tuple(labels)
        current = tuple(values or (False,) * len(labels))
        columns = max(1, int(columns))
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(10)
        for index, label in enumerate(labels):
            check = CheckForm(
                str(label),
                checked=bool(current[index]) if index < len(current) else False,
            )
            layout.addWidget(check, index // columns, index % columns)
            self._checks.append(check)
        for column in range(columns):
            layout.setColumnStretch(column, 1)

    def values(self) -> tuple[bool, ...]:
        return tuple(check.isChecked() for check in self._checks)

    def set_values(self, values) -> None:
        for check, value in zip(self._checks, values):
            check.setChecked(bool(value))
