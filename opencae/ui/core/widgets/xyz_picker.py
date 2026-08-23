"""Provides the canonical segmented XYZ input with optional viewport picking."""

from __future__ import annotations

from PyQt6.QtCore import QSize, QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from opencae.ui.core.icon_factory import IconKind, make_icon
from opencae.ui.core.theme import PALETTE
from opencae.ui.templates import (
    CONTROL_GROUP_SPACING,
    apply_inline_action_size,
    apply_primary_control_height,
)


class XYZPicker(QWidget):
    """Edit one XYZ vector and optionally replace it from a viewport reference."""

    pick_requested = pyqtSignal(object, object, object)
    cancel_requested = pyqtSignal()
    changed = pyqtSignal()

    def __init__(
        self,
        values=(0.0, 0.0, 0.0),
        *,
        allowed=(),
        value_kind="point",
        suffix="",
        parent=None,
    ):
        """Build a segmented three-component editor using canonical control metrics."""
        super().__init__(parent)
        self.allowed = tuple(allowed)
        self.value_kind = str(value_kind)
        self.setObjectName("XYZPicker")
        self.setMinimumWidth(0)
        apply_primary_control_height(self)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        unit = str(suffix or "").strip()
        self.editors = []
        segment_names = (
            "XYZFirst",
            "XYZMiddle",
            "XYZLastWithUnit" if unit else "XYZLast",
        )
        for axis, value, object_name in zip("XYZ", values, segment_names):
            editor = QDoubleSpinBox()
            editor.setObjectName(object_name)
            editor.setRange(-1.0e30, 1.0e30)
            editor.setDecimals(8)
            editor.setValue(float(value))
            editor.setPrefix(f"{axis}: ")
            editor.setMinimumWidth(0)
            editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            apply_primary_control_height(editor)
            editor.valueChanged.connect(lambda _value: self.changed.emit())
            self.editors.append(editor)
            layout.addWidget(editor, 1)

        self.unit_label = None
        if unit:
            self.unit_label = QLabel(unit)
            self.unit_label.setObjectName("PrimaryUnitLabel")
            self.unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            apply_primary_control_height(self.unit_label)
            layout.addWidget(self.unit_label)

        self.pick_button = QToolButton()
        self.pick_button.setIcon(make_icon(IconKind.PICK, 18, PALETTE["text"]))
        self.pick_button.setIconSize(QSize(18, 18))
        self.pick_button.setCheckable(True)
        self.pick_button.setObjectName("InlinePickButton")
        self.pick_button.setAccessibleName("Pick in viewport")
        self.pick_button.setToolTip("Pick this value in the viewport")
        apply_inline_action_size(self.pick_button)
        self.pick_button.toggled.connect(self._toggle_pick)
        self.pick_button.setEnabled(bool(self.allowed))
        layout.addSpacing(CONTROL_GROUP_SPACING)
        layout.addWidget(self.pick_button)

        self.setFocusProxy(self.editors[0])

    def value(self):
        """Return the current XYZ tuple."""
        return tuple(editor.value() for editor in self.editors)

    def set_value(self, value):
        """Replace all three components and publish one consolidated change event."""
        values = tuple(float(component) for component in value)
        if len(values) != 3:
            raise ValueError("An XYZ value requires exactly three components")
        for editor, component in zip(self.editors, values):
            blocker = QSignalBlocker(editor)
            editor.setValue(component)
            del blocker
        self.changed.emit()

    def finish_pick(self):
        """End the current viewport-pick state without emitting another request."""
        if self.pick_button.isChecked():
            blocker = QSignalBlocker(self.pick_button)
            self.pick_button.setChecked(False)
            del blocker

    def _toggle_pick(self, active):
        """Begin or cancel the viewport reference workflow."""
        if not active:
            self.cancel_requested.emit()
            return
        if not self.allowed:
            self.finish_pick()
            return
        self.pick_requested.emit(self.allowed, self._apply_reference, self.finish_pick)

    def _apply_reference(self, reference):
        """Extract the appropriate point/direction value from one picked reference."""
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
