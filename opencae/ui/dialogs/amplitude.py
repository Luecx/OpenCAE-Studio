"""Create and edit reusable load amplitudes with tabular/function definitions."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QHeaderView,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from opencae.model.entities.amplitudes import (
    FUNCTION_DEFAULTS,
    FUNCTION_TYPES,
    INTERPOLATIONS,
    TIME_BASES,
    preview_points,
    sample_function,
)
from opencae.model.naming import is_unique
from opencae.ui.core.apply_dialog import ApplyDialog
from opencae.ui.core.widgets import AmplitudeCurvePreview, ChevronComboBox
from opencae.ui.templates import (
    ButtonRole,
    NumericUnitInput,
    SectionHeading,
    apply_primary_control_height,
    button,
    dialog_buttons,
    dialog_layout,
    field_block,
    field_row,
)


class AmplitudeDialog(ApplyDialog):
    """Edit the authoritative point table while optionally generating it from a function."""

    def __init__(
        self,
        parent=None,
        default_name="",
        existing_names=(),
        amplitude=None,
    ):
        super().__init__(parent)
        self.amplitude = amplitude
        self.existing_names = tuple(existing_names)
        self._parameter_widgets: dict[str, NumericUnitInput] = {}

        self.setWindowTitle(f"{'Edit' if amplitude else 'Create'} Amplitude")
        self.setMinimumSize(980, 620)
        root = dialog_layout(self)

        self.name = QLineEdit(
            amplitude.name if amplitude else (default_name or "Amplitude-1")
        )
        apply_primary_control_height(self.name)
        root.addWidget(field_block("Name", self.name))
        root.addWidget(SectionHeading("Amplitude Definition"))

        self.mode = _combo(("Tabular", "Function"), getattr(amplitude, "source_mode", "Tabular"))
        self.time_basis = _combo(TIME_BASES, getattr(amplitude, "time_basis", "Step time"))
        root.addWidget(
            field_row(
                field_block("Definition", self.mode),
                field_block("Time basis", self.time_basis),
            )
        )

        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(18)

        # Function-page construction immediately creates its first live preview,
        # so the preview must exist before either editor page is initialized.
        self.preview = AmplitudeCurvePreview()
        self.stack = QStackedWidget()
        self.stack.setMinimumWidth(430)
        self.stack.addWidget(self._tabular_page(amplitude))
        self.stack.addWidget(self._function_page(amplitude))
        content_layout.addWidget(self.stack, 5)
        content_layout.addWidget(self.preview, 6)
        root.addWidget(content, 1)

        buttons = dialog_buttons(include_apply=True)
        self.bind_buttons(buttons, True)
        root.addWidget(buttons)

        self.mode.currentIndexChanged.connect(self._mode_changed)
        self.time_basis.currentIndexChanged.connect(lambda _index: self._update_preview())
        self._mode_changed()

    def _tabular_page(self, amplitude):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.interpolation = _combo(
            INTERPOLATIONS,
            getattr(amplitude, "interpolation", "Linear")
            if getattr(amplitude, "source_mode", "Tabular") == "Tabular"
            else "Linear",
        )
        layout.addWidget(field_block("Interpolation", self.interpolation))

        self.table = _AmplitudePointTable()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(("Time", "Value"))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(False)
        self.table.setMinimumHeight(300)
        points = getattr(amplitude, "points", ((0.0, 0.0), (1.0, 1.0)))
        self._set_table_points(points)
        layout.addWidget(self.table, 1)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)
        controls.addWidget(button("Add point", clicked=self._add_point))
        controls.addWidget(
            button(
                "Delete point",
                role=ButtonRole.DANGER,
                clicked=self._delete_point,
            )
        )
        controls.addStretch(1)
        layout.addLayout(controls)

        self.interpolation.currentIndexChanged.connect(lambda _index: self._update_preview())
        self.table.itemChanged.connect(lambda _item: self._update_preview())
        self.table.pasted.connect(self._update_preview)
        return page

    def _function_page(self, amplitude):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        function_type = getattr(amplitude, "function_type", "Ramp")
        self.function_type = _combo(FUNCTION_TYPES, function_type)
        layout.addWidget(field_block("Function", self.function_type))

        self.parameter_host = QWidget()
        self.parameter_layout = QVBoxLayout(self.parameter_host)
        self.parameter_layout.setContentsMargins(0, 0, 0, 0)
        self.parameter_layout.setSpacing(10)
        layout.addWidget(self.parameter_host)

        self.sample_start = NumericUnitInput(
            getattr(amplitude, "sample_start", 0.0),
            minimum=-1e30,
            maximum=1e30,
            decimals=10,
        )
        self.sample_end = NumericUnitInput(
            getattr(amplitude, "sample_end", 1.0),
            minimum=-1e30,
            maximum=1e30,
            decimals=10,
        )
        self.sample_intervals = QSpinBox()
        self.sample_intervals.setRange(1, 10000)
        self.sample_intervals.setValue(int(getattr(amplitude, "sample_intervals", 100)))
        apply_primary_control_height(self.sample_intervals)
        layout.addWidget(
            field_row(
                field_block("Start time", self.sample_start),
                field_block("End time", self.sample_end),
                field_block("Intervals", self.sample_intervals),
            )
        )
        layout.addStretch(1)

        self._stored_function_parameters = dict(
            getattr(amplitude, "function_parameters", {}) or {}
        )
        self.function_type.currentIndexChanged.connect(self._rebuild_parameters)
        self.sample_start.valueChanged.connect(lambda _value: self._update_preview())
        self.sample_end.valueChanged.connect(lambda _value: self._update_preview())
        self.sample_intervals.valueChanged.connect(lambda _value: self._update_preview())
        self._rebuild_parameters()
        return page

    def _rebuild_parameters(self, _index=None):
        while self.parameter_layout.count():
            item = self.parameter_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._parameter_widgets = {}
        function_type = self.function_type.currentText()
        defaults = dict(FUNCTION_DEFAULTS[function_type])
        if function_type == getattr(self.amplitude, "function_type", None):
            defaults.update(self._stored_function_parameters)
        fields = []
        for key, value in defaults.items():
            editor = NumericUnitInput(
                value,
                minimum=-1e30,
                maximum=1e30,
                decimals=10,
            )
            editor.valueChanged.connect(lambda _value: self._update_preview())
            self._parameter_widgets[key] = editor
            fields.append(field_block(_parameter_label(key), editor))
        if len(fields) <= 2:
            self.parameter_layout.addWidget(field_row(*fields))
        else:
            for start in range(0, len(fields), 2):
                self.parameter_layout.addWidget(field_row(*fields[start:start + 2]))
        self._update_preview()

    def _mode_changed(self, _index=None):
        self.stack.setCurrentIndex(0 if self.mode.currentText() == "Tabular" else 1)
        self._update_preview()

    def _add_point(self):
        points = self._table_points(allow_invalid=True)
        row = self.table.currentRow()
        insert_at = row + 1 if row >= 0 else self.table.rowCount()
        if len(points) >= 2:
            if insert_at >= len(points):
                delta = points[-1][0] - points[-2][0]
                time = points[-1][0] + (delta if delta > 0 else 1.0)
                value = points[-1][1]
            elif insert_at > 0:
                before = points[insert_at - 1]
                after = points[insert_at]
                time = 0.5 * (before[0] + after[0])
                value = 0.5 * (before[1] + after[1])
            else:
                time = points[0][0] - 1.0
                value = points[0][1]
        elif points:
            time, value = points[-1][0] + 1.0, points[-1][1]
        else:
            time, value = 0.0, 0.0
        self.table.blockSignals(True)
        self.table.insertRow(insert_at)
        self.table.setItem(insert_at, 0, QTableWidgetItem(_number_text(time)))
        self.table.setItem(insert_at, 1, QTableWidgetItem(_number_text(value)))
        self.table.blockSignals(False)
        self.table.selectRow(insert_at)
        self._update_preview()

    def _delete_point(self):
        if self.table.rowCount() <= 2:
            return
        row = self.table.currentRow()
        if row < 0:
            row = self.table.rowCount() - 1
        self.table.removeRow(row)
        self._update_preview()

    def _set_table_points(self, points):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for time, value in points:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(_number_text(time)))
            self.table.setItem(row, 1, QTableWidgetItem(_number_text(value)))
        self.table.blockSignals(False)

    def _table_points(self, allow_invalid=False):
        points = []
        for row in range(self.table.rowCount()):
            try:
                time = float(self.table.item(row, 0).text().strip())
                value = float(self.table.item(row, 1).text().strip())
            except (AttributeError, TypeError, ValueError):
                if allow_invalid:
                    continue
                raise ValueError(f"Row {row + 1} contains an invalid time or value")
            points.append((time, value))
        if not allow_invalid:
            if len(points) < 2:
                raise ValueError("Enter at least two amplitude points")
            for previous, current in zip(points, points[1:]):
                if current[0] <= previous[0]:
                    raise ValueError("Amplitude times must be strictly increasing")
        return points

    def _function_parameters(self):
        return {key: widget.value() for key, widget in self._parameter_widgets.items()}

    def _function_points(self):
        return sample_function(
            self.function_type.currentText(),
            self._function_parameters(),
            self.sample_start.value(),
            self.sample_end.value(),
            self.sample_intervals.value(),
        )

    def _update_preview(self):
        try:
            if self.mode.currentText() == "Function":
                points = self._function_points()
                stride = max(1, len(points) // 20)
                knots = points if len(points) <= 32 else [*points[::stride], points[-1]]
                self.preview.set_data(points, knots)
            else:
                knots = self._table_points()
                self.preview.set_data(
                    preview_points(knots, self.interpolation.currentText()),
                    knots,
                )
        except (TypeError, ValueError):
            return

    def validate(self) -> bool:
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Enter an amplitude name.")
            return False
        current = self.amplitude.name if self.amplitude else ""
        if not is_unique(name, self.existing_names, current):
            QMessageBox.warning(
                self,
                "Duplicate name",
                f"An amplitude named '{name}' already exists.",
            )
            return False
        try:
            if self.mode.currentText() == "Function":
                self._function_points()
            else:
                self._table_points()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid amplitude", str(exc))
            return False
        return True

    def values(self) -> dict:
        mode = self.mode.currentText()
        if mode == "Function":
            points = self._function_points()
            interpolation = "Linear"
        else:
            points = self._table_points()
            interpolation = self.interpolation.currentText()
        return {
            "name": self.name.text().strip(),
            "points": points,
            "interpolation": interpolation,
            "time_basis": self.time_basis.currentText(),
            "source_mode": mode,
            "function_type": self.function_type.currentText(),
            "function_parameters": self._function_parameters(),
            "sample_start": self.sample_start.value(),
            "sample_end": self.sample_end.value(),
            "sample_intervals": self.sample_intervals.value(),
        }

    def prepare_new(self, default_name, existing_names):
        self.amplitude = None
        self.existing_names = tuple(existing_names)
        self.name.setText(default_name)
        self.mode.setCurrentText("Tabular")
        self.time_basis.setCurrentText("Step time")
        self.interpolation.setCurrentText("Linear")
        self._set_table_points(((0.0, 0.0), (1.0, 1.0)))
        self.function_type.setCurrentText("Ramp")
        self.sample_start.setValue(0.0)
        self.sample_end.setValue(1.0)
        self.sample_intervals.setValue(100)
        self._stored_function_parameters = {}
        self._rebuild_parameters()
        self._update_preview()


class _AmplitudePointTable(QTableWidget):
    """Editable numeric table with spreadsheet-friendly multi-row paste."""

    pasted = pyqtSignal()

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Paste):
            text = QApplication.clipboard().text().strip()
            rows = [line for line in text.splitlines() if line.strip()]
            parsed = []
            for line in rows:
                columns = [
                    value.strip()
                    for value in line.replace(",", "\t").split("\t")
                    if value.strip()
                ]
                if len(columns) < 2:
                    continue
                try:
                    parsed.append((float(columns[0]), float(columns[1])))
                except ValueError:
                    continue
            if parsed:
                start = max(0, self.currentRow())
                self.blockSignals(True)
                while self.rowCount() < start + len(parsed):
                    self.insertRow(self.rowCount())
                for offset, (time, value) in enumerate(parsed):
                    row = start + offset
                    self.setItem(row, 0, QTableWidgetItem(_number_text(time)))
                    self.setItem(row, 1, QTableWidgetItem(_number_text(value)))
                self.blockSignals(False)
                self.pasted.emit()
                return
        super().keyPressEvent(event)


def _combo(values, current):
    combo = ChevronComboBox()
    combo.setMinimumWidth(0)
    for value in values:
        combo.addItem(str(value), str(value))
    index = combo.findData(str(current))
    combo.setCurrentIndex(max(0, index))
    apply_primary_control_height(combo)
    return combo


def _parameter_label(key: str) -> str:
    labels = {
        "start_value": "Start value",
        "end_value": "End value",
        "frequency": "Frequency",
        "phase": "Phase (deg)",
        "amplitude": "Amplitude",
        "offset": "Offset",
        "value": "Value",
        "decay": "Decay rate",
    }
    return labels.get(key, key.replace("_", " ").title())


def _number_text(value) -> str:
    return f"{float(value):.12g}"
