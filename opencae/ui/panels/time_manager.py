"""Provides the lower-workspace Time Manager controls and compact frame plot."""

from __future__ import annotations

import math

import numpy as np
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from opencae.results.navigation import field_for_frame, fields_for, frame_keys, step_ids, step_label
from opencae.ui.core.icon_factory import IconKind, make_icon
from opencae.ui.core.theme import PALETTE
from opencae.ui.primitives.buttons import ButtonTimeManagerMedia
from opencae.ui.primitives.inputs import InputTimeManagerSpeed
from opencae.ui.primitives.labels import LabelBody, LabelTimeManagerHeading
from opencae.ui.primitives.radios import RadioForm
from opencae.ui.primitives.selects import SelectTimeManagerStep
from opencae.ui.primitives.sliders import SliderHorizontal
from opencae.ui.templates import field_block


class TimeManagerPlot(QWidget):
    """Draw the active frame path and allow direct frame selection."""

    frame_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._frames = []
        self._current = 0
        self.setMinimumHeight(130)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_frames(self, frames, current=0):
        self._frames = list(frames)
        self._current = max(0, min(int(current), max(0, len(self._frames) - 1)))
        self.update()

    def set_current(self, index):
        self._current = max(0, min(int(index), max(0, len(self._frames) - 1)))
        self.update()

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(PALETTE["panel"]))
        if not self._frames:
            painter.setPen(QColor(PALETTE["muted"]))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No result frames")
            return
        margin = 24
        width = max(1, self.width() - 2 * margin)
        height = max(1, self.height() - 2 * margin)
        count = len(self._frames)
        baseline = margin + height * 0.5
        accent = QColor(PALETTE["accent"])
        muted = QColor(PALETTE["muted"])
        painter.setPen(QPen(muted, 1.0))
        painter.drawLine(margin, int(baseline), margin + width, int(baseline))
        points = []
        for index in range(count):
            x = margin + (0 if count == 1 else width * index / (count - 1))
            points.append((x, baseline))
        for index, (x, y) in enumerate(points):
            radius = 5 if index == self._current else 3
            painter.setBrush(accent if index == self._current else muted)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(x - radius), int(y - radius), radius * 2, radius * 2)

    def mousePressEvent(self, event):
        if not self._frames or event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        margin = 24
        width = max(1, self.width() - 2 * margin)
        if len(self._frames) == 1:
            index = 0
        else:
            fraction = (event.position().x() - margin) / width
            index = round(max(0.0, min(1.0, fraction)) * (len(self._frames) - 1))
        self.frame_selected.emit(int(index))


class TimeManagerPanel(QWidget):
    """Own result-frame navigation and playback state for the lower workspace."""

    frame_changed = pyqtSignal(object, object, object)
    summary_changed = pyqtSignal(str, str)

    FRAME_INTERVAL_MS = 16
    ACROSS_BASE_FPS = 6.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._result = None
        self._field = None
        self._options = {}
        self._playback_options = None
        self._frames = []
        self._current_index = 0
        self._frame_grid_cache = {}
        self._timer = QTimer(self)
        self._timer.setInterval(self.FRAME_INTERVAL_MS)
        self._timer.timeout.connect(self._advance_playback)
        self._phase = 0.0
        self._last_tick = None
        self._build()

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(290)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(14, 10, 14, 10)
        side.setSpacing(8)

        side.addWidget(self._heading("Step"))
        self.step = SelectTimeManagerStep(parent=self.sidebar)
        self.step.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.step.currentIndexChanged.connect(self._step_changed)
        side.addWidget(self.step)

        side.addSpacing(2)
        side.addWidget(self._heading("Playback"))
        self.current_frame = RadioForm("Current frame", parent=self.sidebar)
        self.across_frames = RadioForm("Across frames", checked=True, parent=self.sidebar)
        self.current_frame.toggled.connect(self._mode_changed)
        self.across_frames.toggled.connect(self._mode_changed)
        side.addWidget(self.current_frame)
        side.addWidget(self.across_frames)

        self.controls_row = QWidget(self.sidebar)
        controls = QHBoxLayout(self.controls_row)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(4)
        self.first_button = self._media_button("first", "First frame")
        self.previous_button = self._media_button("previous", "Previous frame")
        self.play_button = self._media_button("play", "Play")
        self.stop_button = self._media_button("stop", "Stop")
        self.next_button = self._media_button("next", "Next frame")
        self.last_button = self._media_button("last", "Last frame")
        self.loop_button = self._media_button("loop", "Loop", checkable=True)
        for button in (
            self.first_button,
            self.previous_button,
            self.play_button,
            self.stop_button,
            self.next_button,
            self.last_button,
            self.loop_button,
        ):
            button.setParent(self.controls_row)
            controls.addWidget(button)
        controls.addStretch(1)
        controls.addSpacing(1)
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

        side.addSpacing(1)
        side.addWidget(self._heading("Speed"))
        speed_row = QWidget()
        speed_layout = QHBoxLayout(speed_row)
        speed_layout.setContentsMargins(0, 0, 0, 0)
        speed_layout.setSpacing(8)
        self.speed_slider = SliderHorizontal(
            minimum=25,
            maximum=400,
            value=100,
            parent=speed_row,
        )
        self.speed = InputTimeManagerSpeed(parent=speed_row)
        self.speed_slider.valueChanged.connect(self._speed_slider_changed)
        self.speed.valueChanged.connect(self._speed_spin_changed)
        speed_layout.addWidget(self.speed_slider, 1)
        speed_layout.addWidget(self.speed)
        side.addWidget(speed_row)
        side.addStretch(1)
        root.addWidget(self.sidebar, 0)

        # Keep compatibility labels as state holders for callers/tests, but the
        # visible frame summary is hosted in the native lower dock tab strip.
        self.total_frames = LabelBody("0", parent=self)
        self.total_frames.hide()
        self.current_frame_label = LabelBody("—", parent=self)
        self.current_frame_label.hide()

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self.plot = TimeManagerPlot()
        self.plot.frame_selected.connect(self._select_frame)
        content_layout.addWidget(self.plot, 1)
        root.addWidget(content, 1)

    @staticmethod
    def _heading(text):
        return LabelTimeManagerHeading(text)

    @staticmethod
    def _media_button(kind, tooltip, *, checkable=False):
        return ButtonTimeManagerMedia(
            icon=_playback_icon(kind),
            tooltip=tooltip,
            checkable=checkable,
        )

    def set_display_state(self, result, field, options):
        """Consume the authoritative Results-ribbon display state."""
        self._stop_playback(restore=False)
        self._result = result
        self._field = field
        self._options = dict(options or {})
        self._playback_options = None
        self._frame_grid_cache.clear()
        self._sync_step_selector()
        self._sync_frames()

    def clear(self):
        self._stop_playback(restore=False)
        self._result = None
        self._field = None
        self._options = {}
        self._playback_options = None
        self._frames = []
        self._frame_grid_cache.clear()
        self.step.clear()
        self.total_frames.setText("0")
        self.current_frame_label.setText("—")
        self.summary_changed.emit("0", "—")
        self.plot.set_frames(())

    def _sync_step_selector(self):
        current = self.step.currentData()
        self.step.blockSignals(True)
        self.step.clear()
        if self._result is not None and self._field is not None:
            fields = tuple(getattr(self._result, "fields", ()))
            for index, step_id in enumerate(step_ids(fields)):
                self.step.addItem(step_label(self._result, step_id, index), step_id)
        if current is not None:
            index = self.step.findData(current)
            if index >= 0:
                self.step.setCurrentIndex(index)
        self.step.blockSignals(False)

    def _sync_frames(self):
        if self._result is None or self._field is None:
            self._frames = []
        else:
            fields = tuple(getattr(self._result, "fields", ()))
            step_id = self.step.currentData()
            if step_id is None:
                ids = step_ids(fields)
                step_id = ids[0] if ids else None
            self._frames = list(frame_keys(fields, step_id)) if step_id is not None else []
        self._current_index = max(0, min(self._current_index, max(0, len(self._frames) - 1)))
        self.total_frames.setText(str(len(self._frames)))
        self.current_frame_label.setText(
            str(self._current_index + 1) if self._frames else "—"
        )
        self.summary_changed.emit(
            self.total_frames.text(),
            self.current_frame_label.text(),
        )
        self.plot.set_frames(self._frames, self._current_index)
        self._refresh_buttons()

    def _step_changed(self, *_):
        self._current_index = 0
        self._frame_grid_cache.clear()
        self._sync_frames()
        self._emit_current()

    def _mode_changed(self, *_):
        if self.sender() is self.current_frame and self.current_frame.isChecked():
            self.across_frames.setChecked(False)
        elif self.sender() is self.across_frames and self.across_frames.isChecked():
            self.current_frame.setChecked(False)

    def _select_frame(self, index):
        if not self._frames:
            return
        target = max(0, min(int(index), len(self._frames) - 1))
        if target == self._current_index:
            self.plot.set_current(target)
            return
        self._current_index = target
        self.current_frame_label.setText(str(target + 1))
        self.summary_changed.emit(
            self.total_frames.text(),
            self.current_frame_label.text(),
        )
        self.plot.set_current(target)
        self._emit_current()
        self._refresh_buttons()

    def _play(self):
        if not self._frames:
            return
        self._phase = 0.0
        self._last_tick = None
        self._timer.start()
        self._refresh_buttons()

    def _stop_playback(self, *, restore):
        was_active = self._timer.isActive()
        self._timer.stop()
        self._last_tick = None
        if restore and was_active:
            self._emit_current()
        self._refresh_buttons()

    def _advance_playback(self):
        if not self._frames:
            self._stop_playback(restore=False)
            return
        import time

        now = time.monotonic()
        previous = self._last_tick
        self._last_tick = now
        if previous is None:
            return
        elapsed = max(0.0, now - previous)
        speed = max(0.25, float(self.speed.value()))
        if self.current_frame.isChecked():
            self._phase += elapsed * speed
            factor = math.sin(self._phase * 2.0 * math.pi)
            if self._phase >= 1.0:
                if self.loop_button.isChecked():
                    self._phase %= 1.0
                else:
                    self._stop_playback(restore=True)
                    return
            self._emit_scaled(factor)
            return
        frame_advance = elapsed * self.ACROSS_BASE_FPS * speed
        self._phase += frame_advance
        target = int(self._phase)
        if target <= 0:
            return
        self._phase -= target
        next_index = self._current_index + target
        if next_index >= len(self._frames):
            if self.loop_button.isChecked():
                next_index %= len(self._frames)
            else:
                self._select_frame(len(self._frames) - 1)
                self._stop_playback(restore=False)
                return
        self._select_frame(next_index)

    def _emit_current(self):
        if not self._frames or self._result is None or self._field is None:
            return
        field, grid = self._frame_payload(self._current_index)
        if field is None:
            return
        self.frame_changed.emit(field, grid, dict(self._options))

    def _emit_scaled(self, factor):
        field, grid = self._frame_payload(self._current_index)
        if field is None or grid is None:
            return
        scaled = grid.copy(deep=True)
        scalar = _scalar_name(field)
        if scalar and scalar in scaled.point_data:
            scaled.point_data[scalar] = np.asarray(scaled.point_data[scalar]) * float(factor)
        displacement = _displacement_keys(scaled)
        if displacement:
            for key in displacement:
                scaled.point_data[key] = np.asarray(scaled.point_data[key]) * float(factor)
        self.frame_changed.emit(field, scaled, dict(self._options))

    def _frame_payload(self, index):
        if self._result is None or self._field is None or not self._frames:
            return None, None
        index = max(0, min(int(index), len(self._frames) - 1))
        frame_id, _value = self._frames[index]
        step_id = self.step.currentData()
        fields = tuple(getattr(self._result, "fields", ()))
        field = field_for_frame(self._field, fields, step_id, frame_id)
        if field is None:
            return None, None
        cache_key = (step_id, frame_id, getattr(field, "name", None), getattr(field, "metadata", {}).get("component"))
        if cache_key not in self._frame_grid_cache:
            loader = getattr(self._result, "load_field_grid", None)
            if not callable(loader):
                return field, None
            self._frame_grid_cache[cache_key] = loader(field)
        return field, self._frame_grid_cache[cache_key]

    def _speed_slider_changed(self, value):
        numeric = max(0.25, min(4.0, float(value) / 100.0))
        if abs(self.speed.value() - numeric) <= 1.0e-12:
            return
        self.speed.blockSignals(True)
        self.speed.setValue(numeric)
        self.speed.blockSignals(False)

    def _speed_spin_changed(self, value):
        target = int(round(max(0.25, min(4.0, float(value))) * 100.0))
        if self.speed_slider.value() == target:
            return
        self.speed_slider.blockSignals(True)
        self.speed_slider.setValue(target)
        self.speed_slider.blockSignals(False)

    def _refresh_buttons(self):
        active = bool(self._frames)
        for button in (
            self.first_button,
            self.previous_button,
            self.play_button,
            self.stop_button,
            self.next_button,
            self.last_button,
            self.loop_button,
        ):
            button.setEnabled(active)
        self.first_button.setEnabled(active and self._current_index > 0)
        self.previous_button.setEnabled(active and self._current_index > 0)
        self.next_button.setEnabled(active and self._current_index + 1 < len(self._frames))
        self.last_button.setEnabled(active and self._current_index + 1 < len(self._frames))
        self.stop_button.setEnabled(self._timer.isActive())
        self.play_button.setEnabled(active and not self._timer.isActive())


def _scalar_name(field):
    metadata = getattr(field, "metadata", {}) or {}
    component = metadata.get("component")
    name = getattr(field, "name", None)
    return f"{name}:{component}" if name and component else name


def _displacement_keys(grid):
    candidates = (("U1", "U2", "U3"), ("u", "v", "w"))
    for keys in candidates:
        if all(key in grid.point_data for key in keys):
            return keys
    return None


def _playback_icon(kind, size=16):
    """Create a crisp monochrome transport icon from application palette colors."""
    if kind == "play":
        return make_icon(IconKind.RUN, size)
    if kind == "stop":
        return make_icon(IconKind.STOP, size)
    if kind == "previous":
        return make_icon(IconKind.PREVIOUS_FRAME, size)
    if kind == "next":
        return make_icon(IconKind.NEXT_FRAME, size)
    color = QColor(PALETTE["text"])
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(color, max(1.2, size / 10.0)))
    painter.setBrush(color)
    if kind in {"first", "last"}:
        left = kind == "first"
        x_bar = size * (0.25 if left else 0.75)
        x_tip = size * (0.70 if left else 0.30)
        x_base = size * (0.43 if left else 0.57)
        painter.drawLine(int(x_bar), int(size * 0.22), int(x_bar), int(size * 0.78))
        polygon = QPolygonF()
        from PyQt6.QtCore import QPointF
        polygon.append(QPointF(x_tip, size * 0.22))
        polygon.append(QPointF(x_tip, size * 0.78))
        polygon.append(QPointF(x_base, size * 0.50))
        painter.drawPolygon(polygon)
    elif kind == "loop":
        path = QPainterPath()
        path.moveTo(size * 0.24, size * 0.40)
        path.cubicTo(size * 0.30, size * 0.20, size * 0.70, size * 0.20, size * 0.76, size * 0.40)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        path = QPainterPath()
        path.moveTo(size * 0.76, size * 0.60)
        path.cubicTo(size * 0.70, size * 0.80, size * 0.30, size * 0.80, size * 0.24, size * 0.60)
        painter.drawPath(path)
    painter.end()
    return QIcon(pixmap)
