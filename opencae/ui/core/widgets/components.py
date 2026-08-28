"""Provides the shared multi-component numeric editor used by loads and supports."""

from __future__ import annotations

from PyQt6.QtWidgets import QGridLayout, QWidget

from opencae.ui.templates import ComponentField


class ComponentsWidget(QWidget):
    """Arrange numeric vector components as reusable label-above fields."""

    def __init__(
        self,
        labels,
        values=None,
        checkable=False,
        editable=True,
        suffixes=None,
        parent=None,
    ):
        """Build up to three component fields per row while preserving the legacy API."""
        super().__init__(parent)
        self._fields: list[ComponentField] = []
        labels = tuple(labels)
        current = list(values or [None] * len(labels))
        if isinstance(suffixes, str):
            suffixes = (suffixes,) * len(labels)
        units = tuple(suffixes or ("",) * len(labels))

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        # Keep each segmented editor visually independent.  A small real
        # layout gap is preferable to compensating with oversized margins:
        # it prevents neighboring X/Y/Z borders from touching while retaining
        # the compact three-column geometry used throughout the dialogs.
        layout.setHorizontalSpacing(3)
        layout.setVerticalSpacing(12)
        columns = min(3, max(1, len(labels)))
        for index, label in enumerate(labels):
            value = current[index] if index < len(current) else None
            unit = str(units[index] if index < len(units) else "").strip()
            field = ComponentField(
                str(label),
                value,
                unit=unit,
                checkable=bool(checkable),
                editable=bool(editable),
            )
            layout.addWidget(field, index // columns, index % columns)
            self._fields.append(field)
        for column in range(columns):
            layout.setColumnStretch(column, 1)

    def values(self):
        """Return component values in input order, preserving None for inactive fields."""
        return [field.value() for field in self._fields]

    def set_values(self, values):
        """Replace all component values without rebuilding the component grid."""
        for field, value in zip(self._fields, values):
            field.set_value(value)
