"""Search/filter line edit used by navigation and browser surfaces."""

from PyQt6.QtWidgets import QLineEdit, QWidget


class InputSearch(QLineEdit):
    """Single-line search control with a native clear affordance."""

    def __init__(
        self,
        placeholder: str = "Search…",
        *,
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setPlaceholderText(str(placeholder))
        self.setClearButtonEnabled(True)
        if object_name:
            self.setObjectName(object_name)
