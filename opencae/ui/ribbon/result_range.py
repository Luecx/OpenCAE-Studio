"""Provides the result contour-range ribbon control and its compact editor flyout."""

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from opencae.ui.core.icon_factory import IconKind, make_icon
from opencae.ui.templates import (
    PRIMARY_CONTROL_HEIGHT,
    SectionHeading,
    apply_primary_control_height,
    field_block,
)
from opencae.ui.viewport.contour_mapping import (
    DEFAULT_CONTOUR_LEVELS,
    DEFAULT_OUTSIDE_COLOR,
    MAX_CONTOUR_LEVELS,
    MIN_CONTOUR_LEVELS,
)


class ResultRangeButton(QToolButton):
    """Open a compact editor for result range and contour color mapping."""

    range_changed = pyqtSignal(object)
    auto_frame_requested = pyqtSignal()
    auto_frames_requested = pyqtSignal()

    def __init__(self, parent=None):
        """Build the ribbon button and its contour presentation controls."""
        super().__init__(parent)
        self.setText("Contour")
        self.setIcon(make_icon(IconKind.RANGE, 28))
        self.setIconSize(QSize(28, 28))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setProperty("ribbonButton", True)
        self.setFixedSize(82, 70)
        self._data_range = (0.0, 1.0)
        self._colors = {
            "below": DEFAULT_OUTSIDE_COLOR,
            "above": DEFAULT_OUTSIDE_COLOR,
        }

        panel = QWidget()
        panel.setMinimumWidth(380)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        layout.addWidget(SectionHeading("Range"))
        self.minimum = self._field()
        self.maximum = self._field()
        layout.addWidget(field_block("Minimum", self.minimum))
        layout.addWidget(field_block("Maximum", self.maximum))

        auto_row = QWidget()
        auto_layout = QHBoxLayout(auto_row)
        auto_layout.setContentsMargins(0, 0, 0, 0)
        auto_layout.setSpacing(8)
        self.auto_frame = self._auto_button("Auto Frame")
        self.auto_frames = self._auto_button("Auto Frames")
        self.auto_frame.setToolTip("Set the contour range from the current frame")
        self.auto_frames.setToolTip(
            "Set the contour range from this field/component across all frames in the current step"
        )
        auto_layout.addWidget(self.auto_frame, 1)
        auto_layout.addWidget(self.auto_frames, 1)
        layout.addWidget(auto_row)

        layout.addWidget(SectionHeading("Color Mapping"))
        self.continuous = QCheckBox("Continuous color mapping")
        self.continuous.setObjectName("ResultContinuousCheckBox")
        layout.addWidget(self.continuous)

        levels_row = QWidget()
        levels_layout = QHBoxLayout(levels_row)
        levels_layout.setContentsMargins(0, 0, 0, 0)
        levels_layout.setSpacing(8)
        self.levels = QSlider(Qt.Orientation.Horizontal)
        self.levels.setRange(MIN_CONTOUR_LEVELS, MAX_CONTOUR_LEVELS)
        self.levels.setValue(DEFAULT_CONTOUR_LEVELS)
        self.levels.setPageStep(2)
        self.levels.setTickInterval(2)
        self.levels.setToolTip("Number of discrete contour color levels")
        self.level_value = QLabel(str(DEFAULT_CONTOUR_LEVELS))
        self.level_value.setMinimumWidth(24)
        self.level_value.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        levels_layout.addWidget(self.levels, 1)
        levels_layout.addWidget(self.level_value)
        layout.addWidget(field_block("Number of levels", levels_row))

        layout.addWidget(SectionHeading("Outside Range"))
        self.outside_colors = QCheckBox("Color values outside range")
        self.outside_colors.setChecked(True)
        self.outside_colors.setObjectName("ResultOutsideColorsCheckBox")
        layout.addWidget(self.outside_colors)

        # The swatches are deliberately one full-width row below the checkbox.
        # They visually read as the two colorbar end colors rather than as tiny
        # form actions attached to the checkbox label.
        color_row = QWidget()
        color_layout = QHBoxLayout(color_row)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.setSpacing(8)
        self.below_color = self._color_button("below")
        self.above_color = self._color_button("above")
        color_layout.addWidget(self.below_color, 1)
        color_layout.addWidget(self.above_color, 1)
        layout.addWidget(color_row)

        menu = QMenu(self)
        action = QWidgetAction(menu)
        action.setDefaultWidget(panel)
        menu.addAction(action)
        self.setMenu(menu)

        for spin in (self.minimum, self.maximum):
            spin.valueChanged.connect(self._emit)
        self.auto_frame.clicked.connect(self.auto_frame_requested.emit)
        self.auto_frames.clicked.connect(self.auto_frames_requested.emit)
        self.levels.valueChanged.connect(self._levels_changed)
        self.continuous.toggled.connect(self._continuous_changed)
        self.outside_colors.toggled.connect(self._outside_colors_changed)
        self.below_color.clicked.connect(lambda: self._choose_color("below"))
        self.above_color.clicked.connect(lambda: self._choose_color("above"))

    @staticmethod
    def _field():
        """Return one full-width numeric contour limit editor."""
        spin = QDoubleSpinBox()
        spin.setRange(-1e300, 1e300)
        spin.setDecimals(12)
        spin.setMinimumWidth(0)
        apply_primary_control_height(spin)
        return spin

    @staticmethod
    def _auto_button(text):
        """Return a one-shot range calculation button, never a toggle state."""
        button = QToolButton()
        button.setText(text)
        button.setCheckable(False)
        button.setMinimumHeight(PRIMARY_CONTROL_HEIGHT)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.setObjectName("ResultAutoButton")
        return button

    def _color_button(self, name):
        """Return an expanding colorbar end swatch for outside-range values."""
        button = QToolButton()
        button.setMinimumWidth(72)
        button.setFixedHeight(22)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.setObjectName("ResultContourColorButton")
        button.setToolTip(
            "Below-range color" if name == "below" else "Above-range color"
        )
        self._refresh_color_button(button, self._colors[name])
        return button

    @staticmethod
    def _refresh_color_button(button, value):
        color = QColor(value)
        button.setText("")
        button.setStyleSheet(
            "QToolButton {"
            f"background-color: {color.name()};"
            "border: 1px solid rgba(255,255,255,0.28);"
            "border-radius: 3px; padding: 0;"
            "}"
            "QToolButton:hover { border: 1px solid rgba(255,255,255,0.72); }"
        )

    def set_data_range(self, minimum, maximum):
        """Remember the active-frame data range without creating an auto state."""
        self._data_range = (float(minimum), float(maximum))

    def set_range(self, minimum, maximum):
        """Set concrete contour limits and publish them as ordinary fixed values."""
        lower, upper = float(minimum), float(maximum)
        if lower > upper:
            lower, upper = upper, lower
        for spin, value in ((self.minimum, lower), (self.maximum, upper)):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)
        self._data_range = (lower, upper)
        self._emit()

    def apply_data_range(self):
        """Copy the remembered current-frame range into the editable fields."""
        self.set_range(*self._data_range)

    def values(self):
        """Return the complete range and contour-mapping configuration."""
        return {
            "minimum": self.minimum.value(),
            "maximum": self.maximum.value(),
            # Retain these compatibility keys for renderers/persisted options,
            # but Auto is now an action rather than a persistent toggle mode.
            "minimum_auto": False,
            "maximum_auto": False,
            "levels": self.levels.value(),
            "continuous": self.continuous.isChecked(),
            "outside_colors": self.outside_colors.isChecked(),
            "below_color": self._colors["below"],
            "above_color": self._colors["above"],
        }

    def _levels_changed(self, value):
        self.level_value.setText(str(int(value)))
        self._emit()

    def _continuous_changed(self, checked):
        self.levels.setEnabled(not checked)
        self.level_value.setEnabled(not checked)
        self._emit()

    def _outside_colors_changed(self, checked):
        self.below_color.setEnabled(checked)
        self.above_color.setEnabled(checked)
        self._emit()

    def _choose_color(self, name):
        current = QColor(self._colors[name])
        color = QColorDialog.getColor(
            current,
            self,
            "Below-range color" if name == "below" else "Above-range color",
        )
        if not color.isValid():
            return
        self._colors[name] = color.name()
        self._refresh_color_button(
            self.below_color if name == "below" else self.above_color,
            self._colors[name],
        )
        self._emit()

    def _emit(self, *_):
        """Publish the complete contour-range configuration."""
        self.range_changed.emit(self.values())
