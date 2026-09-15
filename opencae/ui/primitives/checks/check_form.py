"""Canonical boolean checkbox used inside forms and option panels."""

from PyQt6.QtWidgets import QCheckBox, QWidget


class CheckForm(QCheckBox):
    def __init__(
        self,
        text: str = "",
        *,
        checked: bool = False,
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(str(text), parent)
        self.setChecked(bool(checked))
        if object_name:
            self.setObjectName(object_name)
