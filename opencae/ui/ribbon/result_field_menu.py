from PyQt6.QtCore import QSignalBlocker, pyqtSignal
from PyQt6.QtWidgets import QFormLayout, QMenu, QToolButton, QWidget, QWidgetAction

from opencae.results.navigation import display_field, fields_for, frame_keys, frame_label, step_ids, step_label
from opencae.ui.core.icon_factory import IconKind, make_icon
from opencae.ui.core.widgets import ChevronComboBox


class ResultFieldButton(QToolButton):
    selection_changed = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent); self.result = None; self.fields = []; self.setText("Choose Field"); self.setIcon(make_icon(IconKind.CONTOUR, 28))
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup); self.setProperty("ribbonButton", True); self.setFixedSize(92, 70)
        panel = QWidget(); form = QFormLayout(panel); form.setContentsMargins(12, 10, 12, 10)
        self.step, self.frame, self.field, self.component = (ChevronComboBox() for _ in range(4))
        for label, combo in (("Step", self.step), ("Frame", self.frame), ("Field", self.field), ("Component", self.component)):
            combo.setMinimumWidth(190); form.addRow(label, combo); combo.currentIndexChanged.connect(self._changed)
        menu = QMenu(self); action = QWidgetAction(menu); action.setDefaultWidget(panel); menu.addAction(action); self.setMenu(menu)

    def set_solution(self, result, fields, preferred=None):
        self.result, self.fields = result, fields; blockers = [QSignalBlocker(c) for c in self._combos()]
        self._steps(preferred); del blockers; self.selection_changed.emit()

    def current_field(self):
        source, component = self.field.currentData(), self.component.currentData(); return display_field(source, component) if source and component else None

    def labels(self):
        return {"Step": self.step.currentText(), "Frame": self.frame.currentText(), "Field": self.field.currentText(), "Component": self.component.currentText()}

    def _steps(self, preferred=None):
        self.step.clear()
        for index, sid in enumerate(step_ids(self.fields)): self.step.addItem(make_icon(IconKind.RESULT_STEP, 16), step_label(self.result, sid, index), sid)
        if preferred: self.step.setCurrentIndex(max(self.step.findData(preferred.metadata.get("step_id", 1)), 0))
        self._frames(preferred)

    def _frames(self, preferred=None):
        self.frame.clear()
        for fid, value in frame_keys(self.fields, self.step.currentData()): self.frame.addItem(make_icon(IconKind.RESULT_FRAME, 16), frame_label(fid, value), (fid, value))
        if preferred:
            target = int(preferred.metadata.get("frame_id", 1)); self.frame.setCurrentIndex(next((i for i in range(self.frame.count()) if self.frame.itemData(i)[0] == target), 0))
        self._fields(preferred)

    def _fields(self, preferred=None):
        self.field.clear(); frame = self.frame.currentData() or (1, 0.0); values = fields_for(self.fields, self.step.currentData(), frame[0])
        for value in values: self.field.addItem(make_icon(IconKind.FIELD, 16), value.name, value)
        if preferred: self.field.setCurrentIndex(next((i for i, value in enumerate(values) if value.name == preferred.name), 0))
        self._components(preferred)

    def _components(self, preferred=None):
        self.component.clear(); source = self.field.currentData()
        if source:
            for name in ("Magnitude", *source.metadata.get("components", ()), *source.metadata.get("derived", ())): self.component.addItem(make_icon(IconKind.CONTOUR, 16), name, name)
            if preferred: self.component.setCurrentText(preferred.metadata.get("component", "Magnitude"))

    def _changed(self, *_):
        sender = self.sender(); blockers = [QSignalBlocker(c) for c in self._combos()]
        if sender is self.step: self._frames()
        elif sender is self.frame: self._fields()
        elif sender is self.field: self._components()
        del blockers; self.selection_changed.emit()

    def _combos(self): return (self.step, self.frame, self.field, self.component)
