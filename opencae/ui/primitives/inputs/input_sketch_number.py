"""Native-height floating-point input used in the Sketcher inspector."""

from PyQt6.QtWidgets import QDoubleSpinBox, QWidget


class InputSketchNumber(QDoubleSpinBox):
    """Keep the Sketcher inspector's existing native spin-box geometry."""

    def __init__(
        self,
        value: float = 0.0,
        *,
        minimum: float = -1.0e30,
        maximum: float = 1.0e30,
        decimals: int = 6,
        step: float | None = None,
        suffix: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setRange(float(minimum), float(maximum))
        self.setDecimals(int(decimals))
        if step is not None:
            self.setSingleStep(float(step))
        if suffix:
            self.setSuffix(str(suffix))
        self.setValue(float(value))
