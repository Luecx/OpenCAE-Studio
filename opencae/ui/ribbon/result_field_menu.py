from PyQt6.QtCore import QSize, QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import QFormLayout, QMenu, QToolButton, QWidget, QWidgetAction

from opencae.results.navigation import display_field, fields_for, frame_keys, frame_label, step_ids, step_label
from opencae.ui.core.icon_factory import IconKind, make_icon
from opencae.ui.core.widgets import ChevronComboBox


class ResultFieldButton(QToolButton):
    selection_changed = pyqtSignal()
    navigation_changed = pyqtSignal(bool, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result = None
        self.fields = []
        self.setText("Field")
        self.setIcon(make_icon(IconKind.RESULT_FIELD, 28))
        self.setIconSize(QSize(28, 28))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setProperty("ribbonButton", True)
        self.setFixedSize(92, 70)
        panel = QWidget()
        form = QFormLayout(panel)
        form.setContentsMargins(12, 10, 12, 10)
        self.step, self.frame, self.field, self.component = (ChevronComboBox() for _ in range(4))
        for label, combo in (("Step", self.step), ("Frame", self.frame), ("Field", self.field), ("Component", self.component)):
            combo.setMinimumWidth(190)
            form.addRow(label, combo)
            combo.currentIndexChanged.connect(self._changed)
        menu = QMenu(self)
        action = QWidgetAction(menu)
        action.setDefaultWidget(panel)
        menu.addAction(action)
        self.setMenu(menu)

    def set_solution(self, result, fields, preferred=None):
        """Load one ResultSet while allowing an explicit no-field geometry view."""
        self.result, self.fields = result, fields
        blockers = [QSignalBlocker(combo) for combo in self._combos()]
        self._steps(preferred)
        if preferred is None:
            # Selecting a ResultSet itself means "show its geometry".  A contour
            # is only activated after a concrete field is selected in the tree or
            # this menu, so loading an FRD can never result in a blank viewport.
            self.field.setCurrentIndex(-1)
            self.component.clear()
        del blockers
        self.selection_changed.emit()
        self._emit_navigation()

    def current_field(self):
        source, component = self.field.currentData(), self.component.currentData()
        return display_field(source, component) if source and component else None

    def labels(self):
        return {
            "Step": self.step.currentText(),
            "Frame": self.frame.currentText(),
            "Field": self.field.currentText(),
            "Component": self.component.currentText(),
        }

    def select_previous_frame(self, *_):
        self._move_frame(-1)

    def select_next_frame(self, *_):
        self._move_frame(1)

    def can_select_previous_frame(self):
        return self.frame.currentIndex() > 0

    def can_select_next_frame(self):
        index = self.frame.currentIndex()
        return index >= 0 and index + 1 < self.frame.count()

    def _move_frame(self, offset):
        target = self.frame.currentIndex() + int(offset)
        if target < 0 or target >= self.frame.count():
            self._emit_navigation()
            return
        field_name = self.field.currentText()
        component_name = self.component.currentText()
        blockers = [QSignalBlocker(combo) for combo in self._combos()]
        self.frame.setCurrentIndex(target)
        self._fields(field_name=field_name, component_name=component_name)
        del blockers
        self.selection_changed.emit()
        self._emit_navigation()

    def _steps(self, preferred=None):
        self.step.clear()
        for index, step_id in enumerate(step_ids(self.fields)):
            self.step.addItem(make_icon(IconKind.RESULT_STEP, 16), step_label(self.result, step_id, index), step_id)
        if preferred:
            step_index = self.step.findData(preferred.metadata.get("step_id", 1))
            if step_index >= 0:
                self.step.setCurrentIndex(step_index)
        self._frames(preferred)

    def _frames(self, preferred=None, field_name=None, component_name=None):
        self.frame.clear()
        for frame_id, value in frame_keys(self.fields, self.step.currentData()):
            self.frame.addItem(make_icon(IconKind.RESULT_FRAME, 16), frame_label(frame_id, value), (frame_id, value))
        if preferred:
            target = int(preferred.metadata.get("frame_id", 1))
            frame_index = next((index for index in range(self.frame.count()) if self.frame.itemData(index)[0] == target), -1)
            if frame_index >= 0:
                self.frame.setCurrentIndex(frame_index)
        self._fields(preferred, field_name, component_name)

    def _fields(self, preferred=None, field_name=None, component_name=None):
        self.field.clear()
        frame = self.frame.currentData() or (1, 0.0)
        values = fields_for(self.fields, self.step.currentData(), frame[0])
        for value in values:
            self.field.addItem(make_icon(IconKind.RESULT_FIELD, 16), value.name, value)
        target_name = preferred.name if preferred else field_name
        if target_name:
            field_index = next((index for index, value in enumerate(values) if value.name == target_name), -1)
            if field_index >= 0:
                self.field.setCurrentIndex(field_index)
        self._components(preferred, component_name)

    def _components(self, preferred=None, component_name=None):
        self.component.clear()
        source = self.field.currentData()
        if not source:
            return
        names = tuple(dict.fromkeys(("Magnitude", *source.metadata.get("components", ()), *source.metadata.get("derived", ()))))
        for name in names:
            self.component.addItem(make_icon(IconKind.CONTOUR, 16), name, name)
        target = preferred.metadata.get("component", "Magnitude") if preferred else component_name
        if target:
            index = self.component.findText(str(target))
            if index >= 0:
                self.component.setCurrentIndex(index)

    def _changed(self, *_):
        sender = self.sender()
        field_name = self.field.currentText()
        component_name = self.component.currentText()
        blockers = [QSignalBlocker(combo) for combo in self._combos()]
        if sender is self.step:
            self._frames(field_name=field_name, component_name=component_name)
        elif sender is self.frame:
            self._fields(field_name=field_name, component_name=component_name)
        elif sender is self.field:
            self._components(component_name=component_name)
        del blockers
        self.selection_changed.emit()
        self._emit_navigation()

    def _emit_navigation(self):
        self.navigation_changed.emit(self.can_select_previous_frame(), self.can_select_next_frame())

    def _combos(self):
        return self.step, self.frame, self.field, self.component
