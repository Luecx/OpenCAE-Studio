"""Reusable selector and central-action strip for executable entities."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from opencae.ui.core.controls import action_button

from .chevron_combo import ChevronComboBox


class EntitySelectorBar(QWidget):
    """Keep one active entity selector synchronized with the project store."""

    entity_changed = pyqtSignal(str)

    def __init__(
        self,
        title,
        store,
        actions,
        entities_provider,
        active_id_provider,
        activate,
        action_ids=(),
        parent=None,
    ):
        super().__init__(parent)
        self.store = store
        self.entities_provider = entities_provider
        self.active_id_provider = active_id_provider
        self.activate = activate
        self.setSizePolicy(
            QSizePolicy.Policy.Maximum,
            QSizePolicy.Policy.Preferred,
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        selector_panel = QFrame(self)
        selector_layout = QVBoxLayout(selector_panel)
        selector_layout.setContentsMargins(9, 8, 9, 4)
        selector_layout.setSpacing(5)

        self.selector = ChevronComboBox()
        self.selector.setMinimumWidth(220)
        self.selector.currentIndexChanged.connect(self._selected)
        selector_layout.addWidget(self.selector)

        label = QLabel(str(title).upper())
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setObjectName("RibbonGroupTitle")
        selector_layout.addWidget(label)
        layout.addWidget(selector_panel)

        if action_ids:
            action_panel = QFrame(self)
            action_panel.setObjectName("RibbonGroup")
            action_layout = QHBoxLayout(action_panel)
            action_layout.setContentsMargins(8, 4, 9, 2)
            action_layout.setSpacing(2)
            for action_id in action_ids:
                action_layout.addWidget(action_button(actions.get(action_id)))
            layout.addWidget(action_panel)

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
