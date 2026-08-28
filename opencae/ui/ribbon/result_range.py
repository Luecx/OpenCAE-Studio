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
        minimum_row, self.minimum, self.minimum_auto = self._field()
        maximum_row, self.maximum, self.maximum_auto = self._field()
        layout.addWidget(field_block("Minimum", minimum_row))
        layout.addWidget(field_block("Maximum", maximum_row))

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
        outside_row = QWidget()
        outside_layout = QHBoxLayout(outside_row)
        outside_layout.setContentsMargins(0, 0, 0, 0)
        outside_layout.setSpacing(8)
        self.outside_colors = QCheckBox("Color values outside range")
        self.outside_colors.setChecked(True)
        self.outside_colors.setObjectName("ResultOutsideColorsCheckBox")
        outside_layout.addWidget(self.outside_colors, 0)
        self.below_color = self._color_button("below")
        self.above_color = self._color_button("above")
        outside_layout.addWidget(self.below_color, 1)
        outside_layout.addWidget(self.above_color, 1)
        layout.addWidget(outside_row)

        menu = QMenu(self)
        action = QWidgetAction(menu)
        action.setDefaultWidget(panel)
        menu.addAction(action)
        self.setMenu(menu)

        for spin in (self.minimum, self.maximum):
            spin.valueChanged.connect(self._emit)
        self.minimum_auto.toggled.connect(
            lambda checked: self._auto_changed("minimum", checked)
        )
        self.maximum_auto.toggled.connect(
            lambda checked: self._auto_changed("maximum", checked)
        )
        self.levels.valueChanged.connect(self._levels_changed)
        self.continuous.toggled.connect(self._continuous_changed)
        self.outside_colors.toggled.connect(self._outside_colors_changed)
        self.below_color.clicked.connect(lambda: self._choose_color("below"))
        self.above_color.clicked.connect(lambda: self._choose_color("above"))
        self.minimum_auto.setChecked(True)
        self.maximum_auto.setChecked(True)

    @staticmethod
    def _field():
        """Return one composite numeric limit row and its child controls."""
        host = QWidget()
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        spin = QDoubleSpinBox()
        spin.setRange(-1e300, 1e300)
        spin.setDecimals(8)
        spin.setMinimumWidth(0)
        apply_primary_control_height(spin)

        auto = QToolButton()
        auto.setText("Auto")
        auto.setCheckable(True)
        auto.setFixedHeight(PRIMARY_CONTROL_HEIGHT)
        auto.setMinimumWidth(58)
        auto.setObjectName("ResultAutoButton")

        row.addWidget(spin, 1)
        row.addWidget(auto)
        return host, spin, auto

    def _color_button(self, name):
        """Return an expanding colorbar end swatch for outside-range values."""
        button = QToolButton()
        button.setMinimumWidth(72)
        button.setFixedHeight(24)
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
        """Replace the automatic limits with the range of the active result field."""
        self._data_range = (float(minimum), float(maximum))
        self._apply_auto("minimum")
        self._apply_auto("maximum")

    def values(self):
        """Return the complete range and contour-mapping configuration."""
        return {
            "minimum": self.minimum.value(),
            "maximum": self.maximum.value(),
            "minimum_auto": self.minimum_auto.isChecked(),
            "maximum_auto": self.maximum_auto.isChecked(),
            "levels": self.levels.value(),
            "continuous": self.continuous.isChecked(),
            "outside_colors": self.outside_colors.isChecked(),
            "below_color": self._colors["below"],
            "above_color": self._colors["above"],
        }

    def _auto_changed(self, name, checked):
        """Enable manual editing only when automatic range selection is disabled."""
        getattr(self, name).setEnabled(not checked)
        if checked:
            self._apply_auto(name)
        self._emit()

    def _apply_auto(self, name):
        """Copy the current data-range endpoint into an automatic limit editor."""
        button = getattr(self, name + "_auto")
        if not button.isChecked():
            return
        spin = getattr(self, name)
        spin.blockSignals(True)
        spin.setValue(self._data_range[0 if name == "minimum" else 1])
        spin.blockSignals(False)

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
