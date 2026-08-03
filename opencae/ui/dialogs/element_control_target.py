from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QVBoxLayout, QWidget

from opencae.model.selection import RegionDefinition
from opencae.ui.core.widgets import CompactRegionSelector


class ElementControlTarget(QWidget):
    """Generic element-region editor used by element controls.

    An empty definition means the entire part. All explicit targets use the
    same RegionDefinition representation as loads, sections and constraints.
    """

    changed = pyqtSignal(object)

    def __init__(self, project, definition=None, options=(), pick_callback=None, parent=None):
        super().__init__(parent)
        value = RegionDefinition.from_values(definition)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(7)

        self.entire_part = QCheckBox("Entire part")
        self.entire_part.setChecked(value.empty)
        root.addWidget(self.entire_part)

        self.region = CompactRegionSelector(
            project,
            value,
            options=options,
            pick_callback=pick_callback,
            parent=self,
        )
        root.addWidget(self.region)

        self.entire_part.toggled.connect(self._mode_changed)
        self.region.value_changed.connect(self._region_changed)
        self._mode_changed(self.entire_part.isChecked(), emit=False)

    def definition(self) -> RegionDefinition:
        return RegionDefinition() if self.entire_part.isChecked() else self.region.definition()

    def set_definition(self, value):
        definition = RegionDefinition.from_values(value)
        self.entire_part.setChecked(definition.empty)
        self.region.set_definition(definition)
        self._mode_changed(definition.empty, emit=False)

    def finish_pick(self):
        self.region.finish_pick()

    def _mode_changed(self, entire, emit=True):
        self.region.setEnabled(not entire)
        if emit:
            self.changed.emit(self.definition())

    def _region_changed(self, _definition):
        if not self.entire_part.isChecked():
            self.changed.emit(self.definition())
