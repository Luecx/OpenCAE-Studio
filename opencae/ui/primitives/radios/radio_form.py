"""Canonical radio button used in option panels."""

from PyQt6.QtWidgets import QRadioButton, QWidget


class RadioForm(QRadioButton):
    def __init__(self, text: str = "", *, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(str(text), parent)
        self.setMinimumHeight(36)
        self.setChecked(bool(checked))
