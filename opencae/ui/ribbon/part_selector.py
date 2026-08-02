from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout

from opencae.ui.core.widgets import ChevronComboBox


class PartSelector(QFrame):
    def __init__(self, store, parent=None):
        super().__init__(parent); self.store = store
        layout = QVBoxLayout(self); layout.setContentsMargins(9, 8, 9, 4); layout.setSpacing(5)
        self.combo = ChevronComboBox(); self.combo.setMinimumWidth(190); self.combo.currentTextChanged.connect(self._selected)
        title = QLabel("ACTIVE PART"); title.setAlignment(Qt.AlignmentFlag.AlignCenter); title.setObjectName("RibbonGroupTitle")
        layout.addWidget(self.combo); layout.addWidget(title)
        store.changed.connect(self.refresh); store.active_part_changed.connect(self.refresh); self.refresh()

    def refresh(self, *_):
        current = self.store.active_part(); name = current.name if current else ""
        self.combo.blockSignals(True); self.combo.clear(); self.combo.addItem("No active part")
        self.combo.addItems([part.name for part in self.store.project.parts]); self.combo.setCurrentText(name or "No active part")
        self.combo.blockSignals(False)

    def _selected(self, text):
        part = next((item for item in self.store.project.parts if item.name == text), None)
        if part is not None: self.store.set_active_part(part.id); self.store.select(part)
