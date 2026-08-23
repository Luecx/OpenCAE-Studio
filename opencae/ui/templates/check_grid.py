"""Provides a compact reusable checkbox grid for finite option groups."""

from __future__ import annotations

from PyQt6.QtWidgets import QCheckBox, QGridLayout, QWidget


class CheckGrid(QWidget):
    """Render a small fixed set of boolean options in equal compact columns."""

    def __init__(self, labels, values=None, *, columns: int = 3, parent=None):
        """Create checkboxes from labels and optional initial truth values."""
        super().__init__(parent)
        self._checks: list[QCheckBox] = []
        labels = tuple(labels)
        current = tuple(values or (False,) * len(labels))
        columns = max(1, int(columns))

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(10)
        for index, label in enumerate(labels):
            check = QCheckBox(str(label))
            check.setChecked(bool(current[index]) if index < len(current) else False)
            layout.addWidget(check, index // columns, index % columns)
            self._checks.append(check)
        for column in range(columns):
            layout.setColumnStretch(column, 1)

    def values(self) -> tuple[bool, ...]:
        """Return checkbox states in the same order as the supplied labels."""
        return tuple(check.isChecked() for check in self._checks)

    def set_values(self, values) -> None:
        """Replace checkbox states without changing grid structure."""
        for check, value in zip(self._checks, values):
            check.setChecked(bool(value))
