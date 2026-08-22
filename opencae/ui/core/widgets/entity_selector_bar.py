"""Reusable active-entity selector for executable workflow definitions."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout

from .chevron_combo import ChevronComboBox


class EntitySelectorBar(QFrame):
    """Keep one active entity selector synchronized with the project store."""

    entity_changed = pyqtSignal(str)

    def __init__(
        self,
        title,
        store,
        entities_provider,
        active_id_provider,
        activate,
        parent=None,
    ):
        super().__init__(parent)
        self.store = store
        self.entities_provider = entities_provider
        self.active_id_provider = active_id_provider
        self.activate = activate

        layout = QVBoxLayout(self)
        layout.setContentsMargins(9, 8, 9, 4)
        layout.setSpacing(5)

        self.selector = ChevronComboBox()
        self.selector.setMinimumWidth(220)
        self.selector.currentIndexChanged.connect(self._selected)
        layout.addWidget(self.selector)

        label = QLabel(str(title).upper())
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setObjectName("RibbonGroupTitle")
        layout.addWidget(label)

        store.changed.connect(self.refresh)
        self.refresh()

    def refresh(self, *_):
        active = str(self.active_id_provider() or "")
        self.selector.blockSignals(True)
        self.selector.clear()
        for entity in tuple(self.entities_provider() or ()):
            self.selector.addItem(entity.name, entity.id)
        index = self.selector.findData(active)
        selected_index = index if index >= 0 else (0 if self.selector.count() else -1)
        self.selector.setCurrentIndex(selected_index)
        self.selector.blockSignals(False)
        selected_id = str(self.selector.currentData() or "")
        if selected_id != active:
            self._selected(selected_index)

    def _selected(self, _index):
        entity_id = str(self.selector.currentData() or "")
        self.activate(entity_id)
        self.entity_changed.emit(entity_id)
