"""Status text primitive with an explicit style hook."""

from PyQt6.QtWidgets import QLabel, QWidget


class LabelStatus(QLabel):
    def __init__(
        self,
        text: str = "",
        *,
        object_name: str = "StatusLabel",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(str(text), parent)
        if object_name:
            self.setObjectName(object_name)
