"""Provides the Results ribbon deformation settings flyout."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from opencae.ui.core.icon_factory import IconKind, make_icon
from opencae.ui.primitives.buttons import OptionsButton
from opencae.ui.templates import NumericUnitInput, button, field_block


class ResultDeformationButton(OptionsButton):
    """Open deformation state and scale settings from one ribbon popup."""

    settings_changed = pyqtSignal()
    auto_frame_requested = pyqtSignal()
    auto_frames_requested = pyqtSignal()

    def __init__(self, parent=None):
        """Build an instant popup with explicit on/off radio buttons."""
        super().__init__(
            "Deformed",
            icon=make_icon(IconKind.DEFORMATION, 28),
            icon_size=28,
            width=82,
            height=70,
            parent=parent,
        )

        panel = QWidget()
        panel.setMinimumWidth(320)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        state_row = QWidget()
        state_layout = QHBoxLayout(state_row)
        state_layout.setContentsMargins(0, 0, 0, 0)
        state_layout.setSpacing(16)
        self.disabled = QRadioButton("Off")
        self.enabled = QRadioButton("On")
        self.disabled.setChecked(True)
        self.state_group = QButtonGroup(self)
        self.state_group.addButton(self.disabled)
        self.state_group.addButton(self.enabled)
        state_layout.addWidget(self.disabled)
        state_layout.addWidget(self.enabled)
        state_layout.addStretch(1)
        layout.addWidget(field_block("Deformation", state_row))

        self.scale = NumericUnitInput(
            1.0,
            "",
            minimum=0.0,
            maximum=1e12,
            decimals=15,
        )
        layout.addWidget(field_block("Deformation scaling factor", self.scale))

        auto_row = QWidget()
        auto_layout = QHBoxLayout(auto_row)
        auto_layout.setContentsMargins(0, 0, 0, 0)
        auto_layout.setSpacing(8)
        self.auto_frame = button("Current Frame")
        self.auto_frames = button("All Frames")
        self.auto_frame.setToolTip(
            "Fit the deformation scale to displacement in the current frame"
        )
        self.auto_frames.setToolTip(
            "Fit one deformation scale to displacement across all frames in the current step"
        )
        self.auto_frame.clicked.connect(self.auto_frame_requested.emit)
        self.auto_frames.clicked.connect(self.auto_frames_requested.emit)
        auto_layout.addWidget(self.auto_frame, 1)
        auto_layout.addWidget(self.auto_frames, 1)
        layout.addWidget(field_block("Automatic scaling", auto_row))

        reset_row = QHBoxLayout()
        reset_row.setContentsMargins(0, 0, 0, 0)
        reset_row.addStretch(1)
        reset = button("Reset to 1")
        reset.clicked.connect(lambda: self.scale.setValue(1.0))
        reset_row.addWidget(reset)
        layout.addLayout(reset_row)

        self.set_options_panel(panel)
        self.enabled.toggled.connect(self.settings_changed.emit)
        self.scale.valueChanged.connect(self.settings_changed.emit)

    def values(self):
        """Return whether deformation is enabled and its current display scale."""
        return self.enabled.isChecked(), self.scale.value()

    def set_scale(self, value):
        """Replace the current deformation scale without changing enable state."""
        self.scale.setValue(float(value))
