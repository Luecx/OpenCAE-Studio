"""Native checkbox surface used in the compact Sketcher inspector."""

from PyQt6.QtWidgets import QCheckBox, QWidget


class CheckSketch(QCheckBox):
    """Preserve the Sketcher inspector's existing checkbox geometry and style."""

    def __init__(
        self,
        text: str,
        *,
        checked: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(str(text), parent)
        self.setChecked(bool(checked))
