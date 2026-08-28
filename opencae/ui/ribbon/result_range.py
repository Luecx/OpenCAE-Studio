"""Provides the result contour-range ribbon control and its compact editor flyout."""

from PyQt6.QtCore import QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
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
from opencae.ui.core.theme import PALETTE
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
    auto_bound_requested = pyqtSignal(str, str)

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
        self._syncing_bounds = False
        self._colors = {
            "below": DEFAULT_OUTSIDE_COLOR,
            "above": DEFAULT_OUTSIDE_COLOR,
        }

        panel = QWidget()
        panel.setMinimumWidth(410)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(9)

        layout.addWidget(SectionHeading("Range"))
        self.minimum = self._field()
        self.maximum = self._field()
        self.minimum_frame = self._auto_button("frame")
        self.minimum_frames = self._auto_button("frames")
        self.maximum_frame = self._auto_button("frame")
        self.maximum_frames = self._auto_button("frames")
        layout.addWidget(
            field_block(
                "Minimum",
                self._bound_row(
                    self.minimum,
                    self.minimum_frame,
                    self.minimum_frames,
                ),
            )
        )

        self.symmetric = QToolButton()
        self.symmetric.setObjectName("ResultRangeSymmetryButton")
        self.symmetric.setCheckable(True)
        self.symmetric.setAutoRaise(False)
        self.symmetric.setIcon(_chain_icon(18))
        self.symmetric.setIconSize(QSize(18, 18))
        self.symmetric.setFixedSize(30, 26)
        self.symmetric.setToolTip(
            "Couple minimum and maximum symmetrically around zero"
        )
        link_row = QHBoxLayout()
        link_row.setContentsMargins(0, 0, 0, 0)
        link_row.addStretch(1)
        link_row.addWidget(self.symmetric)
        link_row.addStretch(1)
        layout.addLayout(link_row)

        layout.addWidget(
            field_block(
                "Maximum",
                self._bound_row(
                    self.maximum,
                    self.maximum_frame,
                    self.maximum_frames,
                ),
            )
        )

        layout.addWidget(self._separator())
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

        layout.addWidget(self._separator())
        layout.addWidget(SectionHeading("Outside Range"))
        self.outside_colors = QCheckBox("Color values outside range")
        self.outside_colors.setChecked(True)
        self.outside_colors.setObjectName("ResultOutsideColorsCheckBox")
        layout.addWidget(self.outside_colors)

        color_row = QWidget()
        color_layout = QHBoxLayout(color_row)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.setSpacing(8)
        self.below_color = self._color_button("below")
        self.above_color = self._color_button("above")
        color_layout.addWidget(field_block("Below range", self.below_color), 1)
        color_layout.addWidget(field_block("Above range", self.above_color), 1)
        layout.addWidget(color_row)

        menu = QMenu(self)
        action = QWidgetAction(menu)
        action.setDefaultWidget(panel)
        menu.addAction(action)
        self.setMenu(menu)

        self.minimum.valueChanged.connect(
            lambda value: self._bound_changed("minimum", value)
        )
        self.maximum.valueChanged.connect(
            lambda value: self._bound_changed("maximum", value)
        )
        for bound, scope, button in (
            ("minimum", "frame", self.minimum_frame),
            ("minimum", "frames", self.minimum_frames),
            ("maximum", "frame", self.maximum_frame),
            ("maximum", "frames", self.maximum_frames),
        ):
            button.clicked.connect(
                lambda _checked=False, bound=bound, scope=scope: self.auto_bound_requested.emit(
                    bound, scope
                )
            )
        self.symmetric.toggled.connect(self._symmetric_toggled)
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
    def _auto_button(scope):
        """Return a compact one-shot range calculation icon."""
        button = QToolButton()
        button.setCheckable(False)
        button.setObjectName("ResultRangeAutoIcon")
        button.setIcon(
            make_icon(
                IconKind.RESULT_FRAME if scope == "frame" else IconKind.RANGE,
                16,
            )
        )
        button.setIconSize(QSize(16, 16))
        button.setFixedSize(30, PRIMARY_CONTROL_HEIGHT)
        button.setToolTip(
            "Use value from current frame"
            if scope == "frame"
            else "Use value across all frames in the current step"
        )
        return button

    @staticmethod
    def _bound_row(field, frame_button, frames_button):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(5)
        row_layout.addWidget(field, 1)
        row_layout.addWidget(frame_button)
        row_layout.addWidget(frames_button)
        return row

    @staticmethod
    def _separator():
        line = QWidget()
        line.setObjectName("ResultRangeSeparator")
        line.setFixedHeight(1)
        line.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        line.setStyleSheet(
            f"QWidget#ResultRangeSeparator {{ background: {PALETTE['border_light']}; }}"
        )
        return line

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
        """Remember the active-frame data range without changing fixed limits."""
        self._data_range = (float(minimum), float(maximum))

    def set_range(self, minimum, maximum):
        """Set both concrete contour limits while respecting symmetry coupling."""
        lower, upper = float(minimum), float(maximum)
        if lower > upper:
            lower, upper = upper, lower
        if self.symmetric.isChecked():
            extent = max(abs(lower), abs(upper))
            lower, upper = -extent, extent
        self._set_bounds(lower, upper)
        self._data_range = (float(minimum), float(maximum))
        self._emit()

    def set_bound(self, bound, value):
        """Set one calculated bound, mirroring it when symmetry is enabled."""
        numeric = float(value)
        if self.symmetric.isChecked():
            extent = abs(numeric)
            self._set_bounds(-extent, extent)
        elif bound == "minimum":
            self._set_bounds(numeric, self.maximum.value())
        elif bound == "maximum":
            self._set_bounds(self.minimum.value(), numeric)
        else:
            raise ValueError(f"Unknown contour bound: {bound}")
        self._emit()

    def apply_data_range(self):
        """Copy the remembered current-frame range into the editable fields."""
        self.set_range(*self._data_range)

    def values(self):
        """Return the complete range and contour-mapping configuration."""
        return {
            "minimum": self.minimum.value(),
            "maximum": self.maximum.value(),
            "minimum_auto": False,
            "maximum_auto": False,
            "symmetric": self.symmetric.isChecked(),
            "levels": self.levels.value(),
            "continuous": self.continuous.isChecked(),
            "outside_colors": self.outside_colors.isChecked(),
            "below_color": self._colors["below"],
            "above_color": self._colors["above"],
        }

    def _set_bounds(self, minimum, maximum):
        self._syncing_bounds = True
        try:
            for spin, value in (
                (self.minimum, minimum),
                (self.maximum, maximum),
            ):
                spin.blockSignals(True)
                spin.setValue(float(value))
                spin.blockSignals(False)
        finally:
            self._syncing_bounds = False

    def _bound_changed(self, bound, value):
        if self._syncing_bounds:
            return
        if self.symmetric.isChecked():
            extent = abs(float(value))
            self._set_bounds(-extent, extent)
        self._emit()

    def _symmetric_toggled(self, checked):
        if checked:
            extent = max(abs(self.minimum.value()), abs(self.maximum.value()))
            self._set_bounds(-extent, extent)
        self._emit()

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


def _chain_icon(size):
    """Draw a small neutral chain glyph without relying on platform emoji fonts."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(
        QPen(
            QColor(PALETTE["muted"]),
            max(1.4, size / 11.0),
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
    )
    painter.save()
    painter.translate(size / 2.0, size / 2.0)
    painter.rotate(-35.0)
    link_width = size * 0.58
    link_height = size * 0.30
    painter.drawRoundedRect(
        QRectF(-link_width * 0.72, -link_height / 2.0, link_width, link_height),
        link_height / 2.0,
        link_height / 2.0,
    )
    painter.drawRoundedRect(
        QRectF(-link_width * 0.28, -link_height / 2.0, link_width, link_height),
        link_height / 2.0,
        link_height / 2.0,
    )
    painter.restore()
    painter.end()
    return QIcon(pixmap)
