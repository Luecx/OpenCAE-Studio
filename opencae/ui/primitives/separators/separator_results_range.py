"""One-pixel divider used inside the Results contour-range popup."""

from PyQt6.QtWidgets import QSizePolicy, QWidget

from opencae.ui.foundation.theme import PALETTE


class SeparatorResultsRange(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ResultRangeSeparator")
        self.setFixedHeight(1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.refresh_theme()

    def refresh_theme(self) -> None:
        self.setStyleSheet(
            f"QWidget#ResultRangeSeparator {{ background: {PALETTE['border_light']}; }}"
        )
