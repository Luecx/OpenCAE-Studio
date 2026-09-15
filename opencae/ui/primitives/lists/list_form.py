"""Canonical list widget used in forms and inspectors."""

from PyQt6.QtWidgets import QListWidget, QWidget


class ListForm(QListWidget):
    def __init__(
        self,
        *,
        minimum_height: int | None = None,
        alternating_rows: bool = False,
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if minimum_height is not None:
            self.setMinimumHeight(int(minimum_height))
        self.setAlternatingRowColors(bool(alternating_rows))
        if object_name:
            self.setObjectName(object_name)
