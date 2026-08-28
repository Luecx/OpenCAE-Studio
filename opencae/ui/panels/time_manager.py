"""Provide frame playback and interpolation controls for stored solver results."""

from __future__ import annotations

from math import pi, sin

from PyQt6.QtCore import (
    QElapsedTimer,
    QPointF,
    QRectF,
    QSize,
    QSignalBlocker,
    Qt,
    QTimer,
)
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from opencae.results.navigation import display_field, fields_for, frame_keys
from opencae.ui.core.theme import PALETTE
from opencae.ui.core.widgets import ChevronComboBox
from .time_manager_plot import TimeManagerPlot


def frame_axis(values):
    """Return the stable one-based frame axis and whether solver values are time-like."""
    raw = [float(value) for value in values]
    if not raw:
        return [], False
    strictly_increasing = len(raw) > 1 and all(
        raw[index + 1] > raw[index] + 1.0e-14
        for index in range(len(raw) - 1)
    )
    # Playback speed is expressed in frames/second.  Solver frame values stay
    # available as the plotted y-series but never stretch/compress the x-axis.
    return [float(index + 1) for index in range(len(raw))], strictly_increasing


def frame_bracket(axis, value):
    """Return bounding frame indices and interpolation alpha for one axis value."""
    values = [float(item) for item in axis]
    if not values:
        return 0, 0, 0.0
    target = float(value)
    if target <= values[0]:
        return 0, 0, 0.0
    if target >= values[-1]:
        last = len(values) - 1
        return last, last, 0.0
    for right in range(1, len(values)):
        if target <= values[right]:
            left = right - 1
            span = values[right] - values[left]
            alpha = 0.0 if span <= 1.0e-14 else (target - values[left]) / span
            return left, right, min(max(alpha, 0.0), 1.0)
    last = len(values) - 1
    return last, last, 0.0


def current_frame_amplitude(phase):
    """Run one full signed response cycle: 0 -> +1 -> 0 -> -1 -> 0."""
    value = min(max(float(phase), 0.0), 1.0)
    return sin(2.0 * pi * value)


def _playback_icon(kind: str, size: int = 18) -> QIcon:
    """Draw crisp theme-native playback glyphs without platform media icons."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    color = QColor(PALETTE["text"])
    pen = QPen(color, 1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(color)

    def triangle(points):
        painter.drawPolygon(QPolygonF([QPointF(*point) for point in points]))

    if kind == "play":
        triangle(((5.0, 3.5), (14.5, 9.0), (5.0, 14.5)))
    elif kind == "stop":
        painter.drawRoundedRect(QRectF(5.0, 5.0, 8.0, 8.0), 1.0, 1.0)
    elif kind in {"previous", "first"}:
        triangle(((9.0, 4.0), (4.5, 9.0), (9.0, 14.0)))
        triangle(((14.0, 4.0), (9.5, 9.0), (14.0, 14.0)))
        if kind == "first":
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(QPointF(3.0, 4.0), QPointF(3.0, 14.0))
    elif kind in {"next", "last"}:
        triangle(((4.0, 4.0), (8.5, 9.0), (4.0, 14.0)))
        triangle(((9.0, 4.0), (13.5, 9.0), (9.0, 14.0)))
        if kind == "last":
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(QPointF(15.0, 4.0), QPointF(15.0, 14.0))
    elif kind == "loop":
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(QRectF(3.0, 3.5, 12.0, 10.0), 25 * 16, 155 * 16)
        painter.drawArc(QRectF(3.0, 4.5, 12.0, 10.0), 205 * 16, 155 * 16)
        painter.setBrush(color)
        triangle(((13.0, 2.8), (16.0, 5.0), (12.4, 6.0)))
        triangle(((5.0, 15.2), (2.0, 13.0), (5.6, 12.0)))

    painter.end()
    return QIcon(pixmap)


class TimeManagerPanel(QWidget):
    """Synchronize result playback with the authoritative Results ribbon state."""

    FRAME_INTERVAL_MS = 33

    def __init__(self, results_page=None, viewport=None, parent=None):
        super().__init__(parent)
        self.results_page = results_page
        self.viewport = viewport
        self._result = None
        self._field = None
        self._options = {}
        self._frames = []
        self._frame_values = []
        self._axis = []
        self._has_time_axis = False
        self._current_index = -1
        self._play_position = 0.0
        self._phase = 0.0
        self._playing = False
        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(self.FRAME_INTERVAL_MS)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._tick)
        self._build()
        if self.results_page is not None:
            self.results_page.result_requested.connect(self.set_display_state)
        self._set_available(False)

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 10)
        root.setSpacing(12)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("TimeManagerSidebar")
        self.sidebar.setFixedWidth(250)
        self.sidebar.setStyleSheet(
            "QFrame#TimeManagerSidebar {"
            f"background: {PALETTE['panel_alt']};"
            f"border: 1px solid {PALETTE['border']};"
            "border-radius: 4px;"
            "}"
        )
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(10, 10, 10, 10)
        side.setSpacing(7)

        side.addWidget(self._heading("Playback Mode"))
        mode_row = QWidget()
        mode_layout = QHBoxLayout(mode_row)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(12)
        self.current_frame = QRadioButton("Current frame")
        self.across_frames = QRadioButton("Across frames")
        self.across_frames.setChecked(True)
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.current_frame)
        self.mode_group.addButton(self.across_frames)
        mode_layout.addWidget(self.current_frame)
        mode_layout.addWidget(self.across_frames)
        mode_layout.addStretch(1)
        side.addWidget(mode_row)
        self.current_frame.toggled.connect(self._mode_changed)
        self.across_frames.toggled.connect(self._mode_changed)

        side.addSpacing(3)
        side.addWidget(self._heading("Controls"))
        self.first_button = self._media_button("first", "First frame")
        self.previous_button = self._media_button("previous", "Previous frame")
        self.play_button = self._media_button("play", "Play")
        self.stop_button = self._media_button("stop", "Stop")
        self.next_button = self._media_button("next", "Next frame")
        self.last_button = self._media_button("last", "Last frame")
        self.loop_button = self._media_button("loop", "Loop playback")
        self.loop_button.setCheckable(True)

        self.controls_row = QWidget()
        controls_layout = QHBoxLayout(self.controls_row)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(3)
        for button in (
            self.first_button,
            self.previous_button,
            self.play_button,
            self.stop_button,
            self.next_button,
            self.last_button,
            self.loop_button,
        ):
            controls_layout.addWidget(button)
        controls_layout.addStretch(1)
        side.addWidget(self.controls_row)

        self.first_button.clicked.connect(lambda: self._select_frame(0))
        self.previous_button.clicked.connect(
            lambda: self._select_frame(self._current_index - 1)
        )
        self.play_button.clicked.connect(self._play)
        self.stop_button.clicked.connect(
            lambda: self._stop_playback(restore=True)
        )
        self.next_button.clicked.connect(
            lambda: self._select_frame(self._current_index + 1)
        )
        self.last_button.clicked.connect(
            lambda: self._select_frame(len(self._frames) - 1)
        )

        side.addSpacing(3)
        side.addWidget(self._heading("Speed"))
        speed_row = QWidget()
        speed_layout = QHBoxLayout(speed_row)
        speed_layout.setContentsMargins(0, 0, 0, 0)
        speed_layout.setSpacing(6)
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(25, 400)
        self.speed_slider.setValue(100)
        self.speed = QDoubleSpinBox()
        self.speed.setRange(0.25, 4.0)
        self.speed.setSingleStep(0.25)
        self.speed.setDecimals(2)
        self.speed.setValue(1.0)
        self.speed.setSuffix(" x")
        self.speed.setFixedWidth(76)
        self.speed_slider.valueChanged.connect(self._speed_slider_changed)
        self.speed.valueChanged.connect(self._speed_spin_changed)
        speed_layout.addWidget(self.speed_slider, 1)
        speed_layout.addWidget(self.speed)
        side.addWidget(speed_row)
        side.addStretch(1)
        root.addWidget(self.sidebar, 0)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        info = QHBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(8)
        info.addWidget(self._muted_label("Current step"))
        self.step = ChevronComboBox()
        self.step.setMinimumWidth(180)
        self.step.currentIndexChanged.connect(self._step_selected)
        info.addWidget(self.step)
        info.addStretch(1)
        info.addWidget(self._muted_label("Total frames"))
        self.total_frames = QLabel("0")
        info.addWidget(self.total_frames)
        info.addSpacing(8)
        info.addWidget(self._muted_label("Current frame"))
        self.current_frame_label = QLabel("—")
        self.current_frame_label.setStyleSheet(
            f"color:{PALETTE['accent']};font-weight:600;"
        )
        info.addWidget(self.current_frame_label)
        content_layout.addLayout(info)

        self.plot = TimeManagerPlot()
        self.plot.frame_selected.connect(self._select_frame)
        content_layout.addWidget(self.plot, 1)
        root.addWidget(content, 1)

    @staticmethod
    def _heading(text):
        label = QLabel(text)
        label.setStyleSheet(
            f"color:{PALETTE['muted']};font-weight:600;font-size:9pt;"
        )
        return label

    @staticmethod
    def _muted_label(text):
        label = QLabel(text)
        label.setStyleSheet(f"color:{PALETTE['muted']};")
        return label

    @staticmethod
    def _media_button(kind, tooltip):
        button = QToolButton()
        button.setObjectName("TimeManagerControl")
        button.setIcon(_playback_icon(kind))
        button.setIconSize(QSize(18, 18))
        button.setToolTip(tooltip)
        button.setFixedSize(28, 28)
        return button

    def set_display_state(self, result, field, options):
        """Consume the authoritative Results-ribbon display state."""
        self._stop_playback(restore=False)
        self._result = result
        self._field = field
        self._options = dict(options or {})
        self._sync_step_selector()
        self._sync_frames()

    def _sync_step_selector(self):
        choose = getattr(self.results_page, "choose", None)
        source = getattr(choose, "step", None)
        blocker = QSignalBlocker(self.step)
        self.step.clear()
        if source is not None:
            for index in range(source.count()):
                self.step.addItem(source.itemText(index), source.itemData(index))
            self.step.setCurrentIndex(source.currentIndex())
        del blocker

    def _sync_frames(self):
        choose = getattr(self.results_page, "choose", None)
        fields = list(getattr(choose, "fields", ()) or ())
        if self._result is None or self._field is None or not fields:
            self._frames = []
            self._frame_values = []
            self._axis = []
            self._current_index = -1
            self.total_frames.setText("0")
            self.current_frame_label.setText("—")
            self._refresh_plot()
            self._set_available(False)
            return

        step_id = int(self._field.metadata.get("step_id", 1))
        component = self._field.metadata.get("component", "Magnitude")
        current_frame_id = int(self._field.metadata.get("frame_id", 1))
        compatible = []
        for frame_id, value in frame_keys(fields, step_id):
            source = next(
                (
                    item
                    for item in fields_for(fields, step_id, frame_id)
                    if item.name == self._field.name
                ),
                None,
            )
            if source is None:
                continue
            display = display_field(source, component)
            combo_index = next(
                (
                    index
                    for index in range(choose.frame.count())
                    if (choose.frame.itemData(index) or (None,))[0] == frame_id
                ),
                -1,
            )
            compatible.append((frame_id, float(value), display, combo_index))

        self._frames = compatible
        self._frame_values = [item[1] for item in compatible]
        self._axis, self._has_time_axis = frame_axis(self._frame_values)
        self._current_index = next(
            (
                index
                for index, item in enumerate(compatible)
                if item[0] == current_frame_id
            ),
            0 if compatible else -1,
        )
        self.total_frames.setText(str(len(compatible)))
        self._update_current_label(self._current_index)
        self._refresh_plot()
        self._set_available(bool(compatible))
        self._update_navigation()

    def _refresh_plot(self):
        if not self._frames:
            self.plot.set_series([], [], x_label="Frame", y_label="Value")
            return
        if self.current_frame.isChecked():
            phases = [index / 64.0 for index in range(65)]
            values = [current_frame_amplitude(value) for value in phases]
            self.plot.set_series(
                phases,
                values,
                cursor_x=self._phase if self._playing else None,
                x_label="Time",
                y_label="Scale",
                show_markers=False,
                interactive=False,
            )
            return
        self.plot.set_series(
            self._axis,
            self._frame_values,
            current_index=self._current_index,
            cursor_x=self._play_position if self._playing else None,
            x_label="Frame",
            y_label="Time (s)" if self._has_time_axis else "Solver frame value",
            show_markers=True,
            interactive=True,
        )

    def _set_available(self, available):
        for widget in (
            self.current_frame,
            self.across_frames,
            self.first_button,
            self.previous_button,
            self.play_button,
            self.stop_button,
            self.next_button,
            self.last_button,
            self.loop_button,
            self.step,
            self.speed_slider,
            self.speed,
        ):
            widget.setEnabled(bool(available))

    def _update_navigation(self):
        count = len(self._frames)
        valid = 0 <= self._current_index < count
        self.first_button.setEnabled(valid and self._current_index > 0)
        self.previous_button.setEnabled(valid and self._current_index > 0)
        self.next_button.setEnabled(valid and self._current_index + 1 < count)
        self.last_button.setEnabled(valid and self._current_index + 1 < count)
        self.play_button.setEnabled(
            valid and (self.current_frame.isChecked() or count > 1)
        )
        self.stop_button.setEnabled(valid)

    def _update_current_label(self, index):
        count = len(self._frames)
        self.current_frame_label.setText(
            f"{index + 1} / {count}" if 0 <= index < count else "—"
        )
        if self.across_frames.isChecked():
            self.plot.set_current_index(index)

    def _select_frame(self, index):
        if not self._frames:
            return
        target = min(max(int(index), 0), len(self._frames) - 1)
        self._stop_playback(restore=False)
        combo_index = self._frames[target][3]
        choose = getattr(self.results_page, "choose", None)
        if choose is not None and combo_index >= 0:
            choose.frame.setCurrentIndex(combo_index)
        else:
            self._current_index = target
            self._update_current_label(target)
            self._refresh_plot()
            self._restore_exact()

    def _step_selected(self, index):
        if self.results_page is None or index < 0:
            return
        self._stop_playback(restore=False)
        choose = getattr(self.results_page, "choose", None)
        if choose is not None and index < choose.step.count():
            choose.step.setCurrentIndex(index)

    def _mode_changed(self, _checked=False):
        if self._playing:
            self._stop_playback(restore=True)
        self._phase = 0.0
        self._refresh_plot()
        self._update_navigation()

    def _speed_slider_changed(self, value):
        blocker = QSignalBlocker(self.speed)
        self.speed.setValue(float(value) / 100.0)
        del blocker

    def _speed_spin_changed(self, value):
        blocker = QSignalBlocker(self.speed_slider)
        self.speed_slider.setValue(round(float(value) * 100.0))
        del blocker

    def _play(self):
        if not self._frames or self._current_index < 0:
            return
        if self.across_frames.isChecked() and len(self._frames) < 2:
            return
        self._playing = True
        self._phase = 0.0
        self._play_position = self._axis[self._current_index]
        self._clock.start()
        self._timer.start()
        self._refresh_plot()
        self._tick(initial=True)

    def _tick(self, initial=False):
        if not self._playing:
            return
        elapsed = (
            0.0
            if initial
            else min(max(self._clock.restart() / 1000.0, 0.0), 0.25)
        )
        rate = float(self.speed.value())
        if self.across_frames.isChecked():
            # The playback coordinate is always a one-based frame ordinal, so
            # one speed unit consistently means one frame per second.
            self._play_position += elapsed * rate
            end = self._axis[-1]
            if self._play_position > end + 1.0e-12:
                if self.loop_button.isChecked():
                    self._play_position = self._axis[0]
                else:
                    self._stop_playback(restore=False)
                    self._select_frame(len(self._frames) - 1)
                    return
            left, right, alpha = frame_bracket(
                self._axis,
                self._play_position,
            )
            visible = right if alpha >= 0.5 else left
            self._update_current_label(visible)
            self.plot.set_cursor_x(self._play_position)
            self._render_interpolated(left, right, alpha)
            return

        self._phase += elapsed * rate
        if self._phase > 1.0 + 1.0e-12:
            if self.loop_button.isChecked():
                self._phase = 0.0
            else:
                self._stop_playback(restore=True)
                return
        self.plot.set_cursor_x(self._phase)
        self._render_current_factor(current_frame_amplitude(self._phase))

    def _render_interpolated(self, left, right, alpha):
        if self.viewport is None or self._result is None:
            return
        first = self._frames[left][2]
        second = self._frames[right][2]
        options = self._animation_options([item[2] for item in self._frames])
        options["_animation"] = {
            "mode": "interpolate",
            "next_field": second,
            "alpha": float(alpha),
        }
        self.viewport.scene.show_result(self._result, first, options)

    def _render_current_factor(self, factor):
        if self.viewport is None or self._result is None or self._current_index < 0:
            return
        field = self._frames[self._current_index][2]
        options = self._animation_options([field])
        options["_animation"] = {
            "mode": "factor",
            "factor": float(factor),
        }
        self.viewport.scene.show_result(self._result, field, options)

    def _animation_options(self, fields):
        """Freeze automatic contour limits so changing values remain visually comparable."""
        options = dict(self._options)
        settings = dict(options.get("range", {}) or {})
        loader = getattr(self.results_page, "loader", None)
        source = getattr(self._result, "source_file", "")
        if loader is None or not source or not fields:
            return options
        minimum_auto = settings.get(
            "minimum_auto",
            settings.get("auto", True),
        )
        maximum_auto = settings.get(
            "maximum_auto",
            settings.get("auto", True),
        )
        if not minimum_auto and not maximum_auto:
            return options
        ranges = []
        for field in fields:
            try:
                ranges.append(loader.scalar_range(source, field))
            except (OSError, RuntimeError, TypeError, ValueError):
                continue
        if not ranges:
            return options
        if minimum_auto:
            settings["minimum"] = min(value[0] for value in ranges)
            settings["minimum_auto"] = False
        if maximum_auto:
            settings["maximum"] = max(value[1] for value in ranges)
            settings["maximum_auto"] = False
        options["range"] = settings
        return options

    def _stop_playback(self, *, restore):
        was_playing = self._playing or self._timer.isActive()
        self._playing = False
        self._timer.stop()
        self.plot.set_cursor_x(None)
        if restore and was_playing:
            self._restore_exact()
            self._update_current_label(self._current_index)

    def _restore_exact(self):
        if self.viewport is None or self._result is None or self._field is None:
            return
        self.viewport.scene.show_result(
            self._result,
            self._field,
            dict(self._options),
        )
