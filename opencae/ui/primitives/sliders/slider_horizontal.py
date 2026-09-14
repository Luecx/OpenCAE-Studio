"""Canonical horizontal slider primitive."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSlider, QWidget


class SliderHorizontal(QSlider):
    def __init__(
        self,
        *,
        minimum: int = 0,
        maximum: int = 100,
        value: int = 0,
        tooltip: str = "",
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setRange(int(minimum), int(maximum))
        self.setValue(int(value))
        if tooltip:
            self.setToolTip(tooltip)
        if object_name:
            self.setObjectName(object_name)
