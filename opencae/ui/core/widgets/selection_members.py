from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget


class SelectionMembersWidget(QWidget):
    def __init__(self, members=(), selection_provider=None, parent=None):
        super().__init__(parent)
        self._selection_provider = selection_provider
        self.list = QListWidget()
        self.list.setMinimumHeight(110)
        self.set_members(members)
        hint = QLabel("Select entities in the viewport. Click replaces the selection; Shift+click extends it.")
        hint.setWordWrap(True)
        hint.setObjectName("FieldHint")
        clear = QPushButton("Clear selection")
        clear.clicked.connect(self.list.clear)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.list)
        layout.addWidget(hint)
        layout.addWidget(clear, 0, Qt.AlignmentFlag.AlignLeft)

    def capture(self):
        if self._selection_provider is not None:
            self.set_members(self._selection_provider() or ())

    def set_members(self, members):
        self.list.clear()
        for member in members:
            text = str(member)
            if text and not self.list.findItems(text, Qt.MatchFlag.MatchExactly):
                self.list.addItem(text)

    def members(self) -> list[str]:
        return [self.list.item(index).text() for index in range(self.list.count())]
