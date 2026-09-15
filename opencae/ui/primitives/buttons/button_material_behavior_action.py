"""Compact define/remove action used by material behavior cards."""

from PyQt6.QtWidgets import QToolButton, QWidget


class ButtonMaterialBehaviorAction(QToolButton):
    """Own the material-card action identity without changing its legacy geometry."""

    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("MaterialBehaviorAction")
        self.setCheckable(False)
