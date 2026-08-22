from __future__ import annotations

from PyQt6.QtCore import QSize, QSignalBlocker, pyqtSignal
from PyQt6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QPushButton, QSizePolicy, QWidget

from opencae.ui.core.icon_factory import IconKind, make_icon
from opencae.ui.core.theme import PALETTE


class XYZPicker(QWidget):
    """Shared segmented XYZ input with a viewport-pick action."""

    pick_requested = pyqtSignal(object, object, object)
    cancel_requested = pyqtSignal()
    changed = pyqtSignal()

    def __init__(self, values=(0.0, 0.0, 0.0), *, allowed=(), value_kind="point", suffix="", parent=None):
        super().__init__(parent)
        self.allowed = tuple(allowed)
        self.value_kind = str(value_kind)
        self.setObjectName("XYZPicker")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.editors = []
        segment_names = ("XYZFirst", "XYZMiddle", "XYZLast")
        for axis, value, object_name in zip("XYZ", values, segment_names):
            editor = QDoubleSpinBox()
            editor.setObjectName(object_name)
            editor.setRange(-1.0e30, 1.0e30)
            editor.setDecimals(8)
            editor.setValue(float(value))
            editor.setPrefix(f"{axis}: ")
            editor.setSuffix(str(suffix or ""))
            editor.setMinimumWidth(78)
            editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            editor.valueChanged.connect(lambda _value: self.changed.emit())
            self.editors.append(editor)
            layout.addWidget(editor, 1)

        self.pick_button = QPushButton()
        self.pick_button.setIcon(make_icon(IconKind.PICK, 18, PALETTE["text"]))
        self.pick_button.setIconSize(QSize(18, 18))
        self.pick_button.setFixedSize(34, 34)
        self.pick_button.setCheckable(True)
        self.pick_button.setObjectName("XYZPickButton")
        self.pick_button.setAccessibleName("Pick in viewport")
        self.pick_button.setToolTip("Pick this value in the viewport")
        self.pick_button.toggled.connect(self._toggle_pick)
        self.pick_button.setEnabled(bool(self.allowed))
        layout.addWidget(self.pick_button)

        self.setMinimumWidth(320)
        self.setFocusProxy(self.editors[0])

    def value(self):
        return tuple(editor.value() for editor in self.editors)

    def set_value(self, value):
        values = tuple(float(component) for component in value)
        if len(values) != 3:
            raise ValueError("An XYZ value requires exactly three components")
        for editor, component in zip(self.editors, values):
            blocker = QSignalBlocker(editor)
            editor.setValue(component)
            del blocker
        self.changed.emit()

    def finish_pick(self):
        if self.pick_button.isChecked():
            blocker = QSignalBlocker(self.pick_button)
            self.pick_button.setChecked(False)
            del blocker

    def _toggle_pick(self, active):
        if not active:
            self.cancel_requested.emit()
            return
        if not self.allowed:
            self.finish_pick()
            return
        self.pick_requested.emit(self.allowed, self._apply_reference, self.finish_pick)

    def _apply_reference(self, reference):
        if not reference:
            self.finish_pick()
            return
        if self.value_kind == "direction":
            value = reference.get("direction") or reference.get("normal")
        else:
            value = reference.get("point") or reference.get("origin")
        if value is None:
            self.finish_pick()
            return
        self.set_value(value)
        self.finish_pick()
