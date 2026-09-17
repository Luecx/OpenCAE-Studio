"""Provides the density-visibility controls used by topology monitors."""

from __future__ import annotations

from PyQt6.QtCore import QSignalBlocker, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from opencae.ui.primitives.checks import CheckForm
from opencae.ui.primitives.inputs import InputFormNumber
from opencae.ui.primitives.labels import LabelBody, LabelForm


class TopologyThresholdControl(QWidget):
    """Select automatic constraint matching or a manual density cutoff."""

    threshold_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)
        self.automatic_input = CheckForm("Match active constraint", checked=True)
        self.value_input = InputFormNumber(
            0.3,
            minimum=0.0,
            maximum=1.000001,
            decimals=10,
        )
        self.value_input.setSingleStep(0.01)
        self.value_input.setEnabled(False)
        controls.addWidget(self.automatic_input)
        controls.addStretch(1)
        controls.addWidget(LabelBody("Show density ≥"))
        controls.addWidget(self.value_input)
        layout.addLayout(controls)

        self.summary = LabelForm("Automatic threshold pending")
        layout.addWidget(self.summary)

        self.automatic_input.toggled.connect(self._mode_changed)
        self.value_input.valueChanged.connect(self._value_changed)

    @property
    def automatic(self) -> bool:
        return self.automatic_input.isChecked()

    @property
    def value(self) -> float:
        return float(self.value_input.value())

    def show_automatic_result(
        self,
        threshold: float,
        achieved: float,
        limit: float,
        approximate: bool,
    ) -> None:
        blocker = QSignalBlocker(self.value_input)
        self.value_input.setValue(threshold)
        del blocker
        fallback = " · equal-element fallback" if approximate else ""
        self.summary.setText(
            f"Automatic ρ ≥ {threshold:.10g} · binary constraint "
            f"{achieved:.10g} / {limit:.10g}{fallback}"
        )

    def show_automatic_unavailable(self) -> None:
        self.summary.setText("Automatic matching unavailable; showing all densities")

    def show_manual_result(self) -> None:
        self.summary.setText(f"Manual density threshold ρ ≥ {self.value:.10g}")

    def _mode_changed(self, automatic: bool) -> None:
        self.value_input.setEnabled(not automatic)
        self.threshold_changed.emit()

    def _value_changed(self, _value: float) -> None:
        if not self.automatic:
            self.threshold_changed.emit()
