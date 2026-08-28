"""Provides the density-visibility controls used by topology monitors."""

from __future__ import annotations

from PyQt6.QtCore import QSignalBlocker, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from opencae.ui.templates import apply_primary_control_height


class TopologyThresholdControl(QWidget):
    """Select automatic constraint matching or a manual density cutoff."""

    threshold_changed = pyqtSignal()

    def __init__(self, parent=None):
        """Build the compact threshold row and its explanatory status label."""
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)
        self.automatic_input = QCheckBox("Match active constraint")
        self.automatic_input.setChecked(True)
        self.value_input = QDoubleSpinBox()
        self.value_input.setRange(0.0, 1.000001)
        self.value_input.setDecimals(10)
        self.value_input.setSingleStep(0.01)
        self.value_input.setValue(0.3)
        self.value_input.setEnabled(False)
        apply_primary_control_height(self.value_input)
        controls.addWidget(self.automatic_input)
        controls.addStretch(1)
        controls.addWidget(QLabel("Show density ≥"))
        controls.addWidget(self.value_input)
        layout.addLayout(controls)

        self.summary = QLabel("Automatic threshold pending")
        self.summary.setObjectName("PrimaryFieldLabel")
        layout.addWidget(self.summary)

        self.automatic_input.toggled.connect(self._mode_changed)
        self.value_input.valueChanged.connect(self._value_changed)

    @property
    def automatic(self) -> bool:
        """Return whether the cutoff should match the active constraint."""
        return self.automatic_input.isChecked()

    @property
    def value(self) -> float:
        """Return the currently displayed density cutoff."""
        return float(self.value_input.value())

    def show_automatic_result(
        self,
        threshold: float,
        achieved: float,
        limit: float,
        approximate: bool,
    ) -> None:
        """Display one calculated cutoff without emitting a redraw recursively."""
        blocker = QSignalBlocker(self.value_input)
        self.value_input.setValue(threshold)
        del blocker
        fallback = " · equal-element fallback" if approximate else ""
        self.summary.setText(
            f"Automatic ρ ≥ {threshold:.10g} · binary constraint "
            f"{achieved:.10g} / {limit:.10g}{fallback}"
        )

    def show_automatic_unavailable(self) -> None:
        """Explain that all densities are shown without a usable constraint."""
        self.summary.setText(
            "Automatic matching unavailable; showing all densities"
        )

    def show_manual_result(self) -> None:
        """Describe the active manual density cutoff."""
        self.summary.setText(
            f"Manual density threshold ρ ≥ {self.value:.10g}"
        )

    def _mode_changed(self, automatic: bool) -> None:
        """Enable manual entry only in manual mode and request a redraw."""
        self.value_input.setEnabled(not automatic)
        self.threshold_changed.emit()

    def _value_changed(self, _value: float) -> None:
        """Request a redraw for user-entered values in manual mode."""
        if not self.automatic:
            self.threshold_changed.emit()
