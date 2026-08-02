from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox, QFormLayout, QVBoxLayout, QWidget

from opencae.model.core import EntityRef
from opencae.ui.core.widgets import SelectionMembersWidget


class ElementControlTarget(QWidget):
    changed = pyqtSignal()

    def __init__(self, selection_provider, element_sets=(), targets=(), parent=None):
        super().__init__(parent)
        self.selection_provider = selection_provider
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)
        form = QFormLayout()
        self.source = QComboBox()
        self.source.addItems(("Entire Part", "Viewport Selection", "Element Set"))
        self.mode_box = QComboBox()
        self.mode_box.addItems(("Elements", "Cells", "Faces", "Edges"))
        self.set_box = QComboBox()
        for region in element_sets:
            if hasattr(region, "id"):
                self.set_box.addItem(region.name, region.id)
            else:
                self.set_box.addItem(str(region), "")
        if not element_sets:
            self.source.model().item(2).setEnabled(False)
        form.addRow("Target", self.source)
        form.addRow("Selection", self.mode_box)
        form.addRow("Element Set", self.set_box)
        layout.addLayout(form)

        selected = list(targets)
        set_ref = next((value for value in selected if isinstance(value, EntityRef)), None)
        legacy_set = next(
            (str(value).split(":", 1)[1] for value in selected if str(value).casefold().startswith("elementset:")),
            None,
        )
        initial = [] if set_ref or legacy_set else selected
        self.members = SelectionMembersWidget(initial, selection_provider, display=str)
        layout.addWidget(self.members)
        if set_ref:
            index = self.set_box.findData(set_ref.entity_id)
            if index >= 0:
                self.set_box.setCurrentIndex(index)
            self.source.setCurrentText("Element Set")
        elif legacy_set:
            self.set_box.setCurrentText(legacy_set)
            self.source.setCurrentText("Element Set")
        elif initial:
            self.source.setCurrentText("Viewport Selection")
        for widget in (self.source, self.mode_box, self.set_box):
            widget.currentTextChanged.connect(self._changed)
        self.members.list.model().rowsInserted.connect(lambda *_: self.changed.emit())
        self.members.list.model().rowsRemoved.connect(lambda *_: self.changed.emit())
        self._changed()

    def _changed(self, *_):
        viewport = self.source.currentText() == "Viewport Selection"
        element_set = self.source.currentText() == "Element Set"
        self.mode_box.setVisible(viewport)
        self.members.setVisible(viewport)
        self.set_box.setVisible(element_set)
        self.changed.emit()

    def mode(self):
        return {"Elements": "element", "Cells": "cell", "Faces": "face", "Edges": "edge"}.get(
            self.mode_box.currentText(), "element"
        )

    def targets(self):
        if self.source.currentText() == "Entire Part":
            return []
        if self.source.currentText() == "Element Set":
            entity_id = self.set_box.currentData()
            return [EntityRef(str(entity_id), "ElementSet")] if entity_id else []
        return self.members.members()

    def capture(self):
        if self.source.currentText() == "Viewport Selection":
            self.members.capture()
            self.changed.emit()
