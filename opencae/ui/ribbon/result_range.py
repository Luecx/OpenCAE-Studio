"""Provides the result contour-range ribbon control and its compact editor flyout."""

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import QColorDialog, QHBoxLayout, QVBoxLayout, QWidget

from opencae.ui.core.icon_factory import IconKind, make_icon
from opencae.ui.core.theme import PALETTE
from opencae.ui.primitives.buttons import ButtonFormAction
from opencae.ui.primitives.buttons.button_color_swatch import ButtonColorSwatch
from opencae.ui.primitives.buttons.button_results_range_auto import ButtonResultsRangeAuto
from opencae.ui.primitives.buttons.button_results_range_symmetry import (
    ButtonResultsRangeSymmetry,
)
from opencae.ui.primitives.buttons.button_results_ribbon_options import (
    ButtonResultsRibbonOptions,
)
from opencae.ui.primitives.checks import CheckForm
from opencae.ui.primitives.inputs.input_form_number import InputFormNumber
from opencae.ui.primitives.labels import LabelBody, LabelSection
from opencae.ui.primitives.separators.separator_results_range import (
    SeparatorResultsRange,
)
from opencae.ui.primitives.sliders import SliderHorizontal
from opencae.ui.templates import field_block
from opencae.ui.viewport.contour_mapping import (
    DEFAULT_CONTOUR_LEVELS,
    DEFAULT_OUTSIDE_COLOR,
    MAX_CONTOUR_LEVELS,
    MIN_CONTOUR_LEVELS,
)


class ResultRangeButton(ButtonResultsRibbonOptions):
    """Open a compact editor for result range and contour color mapping."""

    range_changed = pyqtSignal(object)
    auto_bound_requested = pyqtSignal(str, str)
    animation_envelope_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(
            "Contour",
            icon=make_icon(IconKind.RANGE, 28),
            width=82,
            parent=parent,
        )
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

        layout.addWidget(LabelSection("Range"))
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

        self.symmetric = ButtonResultsRangeSymmetry(_chain_icon(18), panel)
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
        self.animation_envelope = ButtonFormAction(
            "Fit animation envelope",
            icon=_range_fit_icon("animation", 18),
            tooltip=(
                "Fit both contour bounds to the values produced by the active "
                "Time Manager animation and its playback limits"
            ),
            object_name="ResultAnimationEnvelopeButton",
            parent=panel,
        )
        self.animation_envelope.clicked.connect(self.animation_envelope_requested.emit)
        layout.addWidget(self.animation_envelope)

        layout.addWidget(SeparatorResultsRange(panel))
        layout.addWidget(LabelSection("Color Mapping"))
        self.continuous = CheckForm(
            "Continuous color mapping",
            object_name="ResultContinuousCheckBox",
            parent=panel,
        )
        layout.addWidget(self.continuous)

        levels_row = QWidget()
        levels_layout = QHBoxLayout(levels_row)
        levels_layout.setContentsMargins(0, 0, 0, 0)
        levels_layout.setSpacing(8)
        self.levels = SliderHorizontal(
            minimum=MIN_CONTOUR_LEVELS,
            maximum=MAX_CONTOUR_LEVELS,
            value=DEFAULT_CONTOUR_LEVELS,
            tooltip="Number of discrete contour color levels",
            parent=levels_row,
        )
        self.levels.setPageStep(2)
        self.levels.setTickInterval(2)
        self.level_value = LabelBody(str(DEFAULT_CONTOUR_LEVELS), parent=levels_row)
        self.level_value.setMinimumWidth(24)
        self.level_value.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        levels_layout.addWidget(self.levels, 1)
        levels_layout.addWidget(self.level_value)
        layout.addWidget(field_block("Number of levels", levels_row))

        layout.addWidget(SeparatorResultsRange(panel))
        layout.addWidget(LabelSection("Outside Range"))
        self.outside_colors = CheckForm(
            "Color values outside range",
            checked=True,
            object_name="ResultOutsideColorsCheckBox",
            parent=panel,
        )
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

        self.set_options_panel(panel)
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
        return InputFormNumber(
            minimum=-1e300,
            maximum=1e300,
            decimals=12,
        )

    @staticmethod
    def _auto_button(scope):
        return ButtonResultsRangeAuto(
            _range_fit_icon(scope, 16),
            tooltip=(
                "Fit this bound to the current frame"
                if scope == "frame"
                else "Fit this bound across all frames in the current step"
            ),
        )

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

    def _color_button(self, name):
        return ButtonColorSwatch(
            self._colors[name],
            tooltip=(
                "Below-range color" if name == "below" else "Above-range color"
            ),
            parent=self,
        )

    @staticmethod
    def _refresh_color_button(button, value):
        button.set_color(value)

    def set_data_range(self, minimum, maximum):
        self._data_range = (float(minimum), float(maximum))

    def set_range(self, minimum, maximum):
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
        self.set_range(*self._data_range)

    def values(self):
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
        self.range_changed.emit(self.values())


def _range_fit_icon(scope, size=16):
    """Draw distinct one-frame, all-frames, and animation-envelope fit glyphs."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    accent = QColor(PALETTE["accent"])
    muted = QColor(PALETTE["muted"])
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(
        QPen(
            muted,
            max(1.0, size / 14.0),
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
    )

    if scope == "frame":
        painter.drawRoundedRect(QRectF(size * .27, size * .16, size * .46, size * .68), 1.5, 1.5)
        painter.setPen(QPen(accent, max(1.25, size / 12.0)))
        painter.drawLine(QPointF(size * .18, size * .28), QPointF(size * .82, size * .28))
        painter.drawLine(QPointF(size * .18, size * .72), QPointF(size * .82, size * .72))
        painter.drawLine(QPointF(size * .50, size * .34), QPointF(size * .50, size * .66))
    elif scope == "frames":
        for x in (.25, .50, .75):
            painter.drawRoundedRect(QRectF(size * (x - .08), size * .22, size * .16, size * .56), 1.2, 1.2)
        painter.setPen(QPen(accent, max(1.25, size / 12.0)))
        painter.drawLine(QPointF(size * .10, size * .18), QPointF(size * .90, size * .18))
        painter.drawLine(QPointF(size * .10, size * .82), QPointF(size * .90, size * .82))
        painter.drawLine(QPointF(size * .50, size * .27), QPointF(size * .50, size * .73))
    else:
        path = QPainterPath(QPointF(size * .10, size * .50))
        path.cubicTo(
            QPointF(size * .24, size * .10),
            QPointF(size * .38, size * .10),
            QPointF(size * .50, size * .50),
        )
        path.cubicTo(
            QPointF(size * .62, size * .90),
            QPointF(size * .76, size * .90),
            QPointF(size * .90, size * .50),
        )
        painter.drawPath(path)
        painter.setPen(QPen(accent, max(1.25, size / 12.0)))
        painter.drawLine(QPointF(size * .14, size * .16), QPointF(size * .86, size * .16))
        painter.drawLine(QPointF(size * .14, size * .84), QPointF(size * .86, size * .84))

    painter.end()
    return QIcon(pixmap)


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
