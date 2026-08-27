"""Provide frame playback and interpolation controls for stored solver results."""

from __future__ import annotations

from math import sin, pi

from PyQt6.QtCore import QElapsedTimer, QSignalBlocker, Qt, QTimer
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSlider,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from opencae.results.navigation import display_field, fields_for, frame_keys
from opencae.ui.core.theme import PALETTE
from opencae.ui.core.widgets import ChevronComboBox
from .time_manager_plot import TimeManagerPlot


def frame_axis(values):
    """Return a unit-spaced 1..N frame axis and whether values form a time axis."""
    raw = [float(value) for value in values]
    if not raw:
        return [], False
    strictly_increasing = len(raw) > 1 and all(
        raw[index + 1] > raw[index] + 1.0e-14
        for index in range(len(raw) - 1)
    )
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


class TimeManagerPanel(QWidget):
    """Synchronize a full-width result timeline with the Results ribbon state."""

    FRAME_INTERVAL_MS = 33

    def __init__(self, results_page=None, viewport=None, parent=None):
        super().__init__(parent)
        self.results_page = results_page
        self.viewport = viewport
        self._result = None
        self._field = None
        self._options = {}
        self._frames = []
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(8)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        mode_title = QLabel("Playback Mode")
        mode_title.setStyleSheet(f"color:{PALETTE['muted']};")
        row.addWidget(mode_title)
        self.current_frame = QRadioButton("Current frame")
        self.across_frames = QRadioButton("Across frames")
        self.across_frames.setChecked(True)
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.current_frame)
        self.mode_group.addButton(self.across_frames)
        row.addWidget(self.current_frame)
        row.addWidget(self.across_frames)
        self.current_frame.toggled.connect(self._mode_changed)
        self.across_frames.toggled.connect(self._mode_changed)

        row.addWidget(self._separator())
        self.first_button = self._media_button(QStyle.StandardPixmap.SP_MediaSkipBackward, "First frame")
        self.previous_button = self._media_button(QStyle.StandardPixmap.SP_MediaSeekBackward, "Previous frame")
        self.play_button = self._media_button(QStyle.StandardPixmap.SP_MediaPlay, "Play")
        self.stop_button = self._media_button(QStyle.StandardPixmap.SP_MediaStop, "Stop")
        self.next_button = self._media_button(QStyle.StandardPixmap.SP_MediaSeekForward, "Next frame")
        self.last_button = self._media_button(QStyle.StandardPixmap.SP_MediaSkipForward, "Last frame")
        self.loop_button = self._media_button(QStyle.StandardPixmap.SP_BrowserReload, "Loop playback")
        self.loop_button.setCheckable(True)
        for button in (
            self.first_button,
            self.previous_button,
            self.play_button,
            self.stop_button,
            self.next_button,
            self.last_button,
            self.loop_button,
        ):
            row.addWidget(button)

        self.first_button.clicked.connect(lambda: self._select_frame(0))
        self.previous_button.clicked.connect(lambda: self._select_frame(self._current_index - 1))
        self.play_button.clicked.connect(self._play)
        self.stop_button.clicked.connect(lambda: self._stop_playback(restore=True))
        self.next_button.clicked.connect(lambda: self._select_frame(self._current_index + 1))
        self.last_button.clicked.connect(lambda: self._select_frame(len(self._frames) - 1))

        row.addWidget(self._separator())
        step_title = QLabel("Current step")
        step_title.setStyleSheet(f"color:{PALETTE['muted']};")
        row.addWidget(step_title)
        self.step = ChevronComboBox()
        self.step.setMinimumWidth(150)
        self.step.currentIndexChanged.connect(self._step_selected)
        row.addWidget(self.step)

        row.addWidget(self._separator())
        total_title = QLabel("Total frames")
        total_title.setStyleSheet(f"color:{PALETTE['muted']};")
        row.addWidget(total_title)
        self.total_frames = QLabel("0")
        row.addWidget(self.total_frames)
        row.addSpacing(5)
        current_title = QLabel("Current frame")
        current_title.setStyleSheet(f"color:{PALETTE['muted']};")
        row.addWidget(current_title)
        self.current_frame_label = QLabel("—")
        self.current_frame_label.setStyleSheet(f"color:{PALETTE['accent']};font-weight:600;")
        row.addWidget(self.current_frame_label)

        row.addStretch(1)
        speed_title = QLabel("Speed")
        speed_title.setStyleSheet(f"color:{PALETTE['muted']};")
        row.addWidget(speed_title)
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(25, 400)
        self.speed_slider.setValue(100)
        self.speed_slider.setFixedWidth(100)
        self.speed = QDoubleSpinBox()
        self.speed.setRange(0.25, 4.0)
        self.speed.setSingleStep(0.25)
        self.speed.setDecimals(2)
        self.speed.setValue(1.0)
        self.speed.setSuffix(" x")
        self.speed.setFixedWidth(78)
        self.speed_slider.valueChanged.connect(self._speed_slider_changed)
        self.speed.valueChanged.connect(self._speed_spin_changed)
        row.addWidget(self.speed_slider)
        row.addWidget(self.speed)
        layout.addLayout(row)

        self.plot = TimeManagerPlot()
        self.plot.frame_selected.connect(self._select_frame)
        layout.addWidget(self.plot, 1)

    def _separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        line.setStyleSheet(f"color:{PALETTE['border']};")
        return line

    def _media_button(self, standard_pixmap, tooltip):
        button = QToolButton()
        button.setObjectName("TimeManagerControl")
        button.setIcon(self.style().standardIcon(standard_pixmap))
        button.setToolTip(tooltip)
        button.setFixedSize(30, 28)
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
            self._axis = []
            self._current_index = -1
            self.total_frames.setText("0")
            self.current_frame_label.setText("—")
            self.plot.set_series([], [])
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
        frame_values = [item[1] for item in compatible]
        self._axis, self._has_time_axis = frame_axis(frame_values)
        self._current_index = next(
            (index for index, item in enumerate(compatible) if item[0] == current_frame_id),
            0 if compatible else -1,
        )
        self.total_frames.setText(str(len(compatible)))
        self._update_current_label(self._current_index)
        self.plot.set_series(
            self._axis,
            frame_values,
            current_index=self._current_index,
            x_label="Frame",
            y_label="Time (s)" if self._has_time_axis else "Solver frame value",
        )
        self._set_available(bool(compatible))
        self._update_navigation()

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
        self.play_button.setEnabled(valid and (self.current_frame.isChecked() or count > 1))
        self.stop_button.setEnabled(valid)

    def _update_current_label(self, index):
        count = len(self._frames)
        self.current_frame_label.setText(
            f"{index + 1} / {count}" if 0 <= index < count else "—"
        )
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
        self._tick(initial=True)

    def _tick(self, initial=False):
        if not self._playing:
            return
        elapsed = 0.0 if initial else min(max(self._clock.restart() / 1000.0, 0.0), 0.25)
        rate = float(self.speed.value())
        if self.across_frames.isChecked():
            # The playback coordinate is an ordinal frame coordinate.  One
            # axis unit is always exactly one result frame, independent of the
            # solver's physical time spacing.
            self._play_position += elapsed * rate
            end = self._axis[-1]
            if self._play_position > end + 1.0e-12:
                if self.loop_button.isChecked():
                    self._play_position = self._axis[0]
                else:
                    self._stop_playback(restore=False)
                    self._select_frame(len(self._frames) - 1)
                    return
            left, right, alpha = frame_bracket(self._axis, self._play_position)
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
        minimum_auto = settings.get("minimum_auto", settings.get("auto", True))
        maximum_auto = settings.get("maximum_auto", settings.get("auto", True))
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
        self.viewport.scene.show_result(self._result, self._field, dict(self._options))
