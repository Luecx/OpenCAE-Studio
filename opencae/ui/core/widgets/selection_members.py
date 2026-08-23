"""Provides the reusable list editor for viewport-selected model members."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from opencae.ui.templates import PRIMARY_CONTROL_HEIGHT, button


class SelectionMembersWidget(QWidget):
    """Display captured selection members and provide consistent list actions."""

    def __init__(
        self,
        members=(),
        selection_provider=None,
        display: Callable | None = None,
        parent=None,
        *,
        formatter: Callable | None = None,
    ):
        """Build the member list using either a current or legacy display callback."""
        super().__init__(parent)
        if display is not None and formatter is not None:
            raise TypeError("Pass either 'display' or the legacy 'formatter' argument, not both.")
        self._selection_provider = selection_provider
        self._display = display or formatter or str

        self.list = QListWidget()
        self.list.setMinimumHeight(110)
        self.set_members(members)

        hint = QLabel(
            "Select entities in the viewport. Click replaces the selection; "
            "Shift+click extends it."
        )
        hint.setWordWrap(True)
        hint.setObjectName("FieldHint")

        actions = QHBoxLayout()
        actions.setSpacing(6)
        if selection_provider is not None:
            capture = button("Use current selection", clicked=self.capture)
            capture.setFixedHeight(PRIMARY_CONTROL_HEIGHT)
            actions.addWidget(capture)
        clear = button("Clear selection", clicked=self.list.clear)
        clear.setFixedHeight(PRIMARY_CONTROL_HEIGHT)
        actions.addWidget(clear)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.list)
        layout.addWidget(hint)
        layout.addLayout(actions)

    def capture(self):
        """Replace the list with the current selection supplied by the viewport."""
        if self._selection_provider is not None:
            self.set_members(self._selection_provider() or ())

    def set_members(self, members):
        """Replace list contents while removing empty labels and duplicate values."""
        self.list.clear()
        for member in members:
            label, value = self._option(member)
            if not label or self._contains(value):
                continue
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, value)
            self.list.addItem(item)

    def members(self) -> list:
        """Return stored member values in current display order."""
        result = []
        for index in range(self.list.count()):
            item = self.list.item(index)
            value = item.data(Qt.ItemDataRole.UserRole)
            result.append(item.text() if value is None else value)
        return result

    def _option(self, member):
        """Normalize an explicit label/value pair or model member for display."""
        if isinstance(member, tuple) and len(member) == 2:
            return str(member[0]), member[1]
        return str(self._display(member)), member

    def _contains(self, value) -> bool:
        """Return whether the current list already stores the supplied member value."""
        return any(
            self.list.item(index).data(Qt.ItemDataRole.UserRole) == value
            for index in range(self.list.count())
        )
