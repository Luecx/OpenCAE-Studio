from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget


class SelectionMembersWidget(QWidget):
    def __init__(
        self,
        members=(),
        selection_provider=None,
        display: Callable | None = None,
        parent=None,
        *,
        formatter: Callable | None = None,
    ):
        super().__init__(parent)
        if display is not None and formatter is not None:
            raise TypeError("Pass either 'display' or the legacy 'formatter' argument, not both.")
        self._selection_provider = selection_provider
        self._display = display or formatter or str
        self.list = QListWidget()
        self.list.setMinimumHeight(110)
        self.set_members(members)
        hint = QLabel("Select entities in the viewport. Click replaces the selection; Shift+click extends it.")
        hint.setWordWrap(True)
        hint.setObjectName("FieldHint")
        capture = QPushButton("Use current selection")
        capture.clicked.connect(self.capture)
        clear = QPushButton("Clear selection")
        clear.clicked.connect(self.list.clear)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.list)
        layout.addWidget(hint)
        if selection_provider is not None:
            layout.addWidget(capture, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(clear, 0, Qt.AlignmentFlag.AlignLeft)

    def capture(self):
        if self._selection_provider is not None:
            self.set_members(self._selection_provider() or ())

    def set_members(self, members):
        self.list.clear()
        for member in members:
            label, value = self._option(member)
            if not label or self._contains(value):
                continue
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, value)
            self.list.addItem(item)

    def members(self) -> list:
        result = []
        for index in range(self.list.count()):
            item = self.list.item(index)
            value = item.data(Qt.ItemDataRole.UserRole)
            result.append(item.text() if value is None else value)
        return result

    def _option(self, member):
        if isinstance(member, tuple) and len(member) == 2:
            return str(member[0]), member[1]
        return str(self._display(member)), member

    def _contains(self, value) -> bool:
        return any(self.list.item(index).data(Qt.ItemDataRole.UserRole) == value for index in range(self.list.count()))
