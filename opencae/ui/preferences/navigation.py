"""Grouped, searchable navigation for the application Settings dialog."""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget


_GROUP_ROLE = Qt.ItemDataRole.UserRole
_PAGE_ROLE = Qt.ItemDataRole.UserRole + 1
_SEARCH_ROLE = Qt.ItemDataRole.UserRole + 2


class PreferencesNavigation(QWidget):
    """Render flat page entries separated by non-selectable semantic group headings."""

    page_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PreferencesSidebar")
        self.setFixedWidth(228)
        self._pages: dict[str, QListWidgetItem] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(10)

        self.search = QLineEdit()
        self.search.setObjectName("PreferencesSearch")
        self.search.setPlaceholderText("Search settings")
        self.search.setClearButtonEnabled(True)
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.setObjectName("PreferencesNavigationList")
        self.list.setSpacing(2)
        self.list.setFrameShape(QListWidget.Shape.NoFrame)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.list, 1)

        self.search.textChanged.connect(self._filter)
        self.list.currentItemChanged.connect(self._current_item_changed)

    def add_page(self, group: str, title: str, keywords=()) -> None:
        """Add one page and searchable field terms under a semantic group heading."""
        group = str(group)
        if not any(
            self.list.item(index).data(_GROUP_ROLE) == group
            and not self.list.item(index).data(_PAGE_ROLE)
            for index in range(self.list.count())
        ):
            header = QListWidgetItem()
            header.setData(_GROUP_ROLE, group)
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            header.setSizeHint(QSize(0, 28))
            self.list.addItem(header)
            label = QLabel(group.upper())
            label.setProperty("preferencesGroupHeader", True)
            self.list.setItemWidget(header, label)

        item = QListWidgetItem(str(title))
        item.setData(_GROUP_ROLE, group)
        item.setData(_PAGE_ROLE, str(title))
        terms = " ".join(str(value) for value in keywords)
        item.setData(_SEARCH_ROLE, f"{title} {group} {terms}".strip())
        item.setSizeHint(QSize(0, 36))
        self.list.addItem(item)
        self._pages[str(title)] = item

    def select_page(self, title: str) -> None:
        """Select a named page, falling back to the first visible page."""
        item = self._pages.get(str(title))
        if item is not None and not item.isHidden():
            self.list.setCurrentItem(item)
            return
        self._select_first_visible()

    def _filter(self, text: str) -> None:
        query = str(text).strip().casefold()
        visible_groups = set()
        for item in self._pages.values():
            search_text = str(item.data(_SEARCH_ROLE) or "").casefold()
            visible = not query or query in search_text
            item.setHidden(not visible)
            if visible:
                visible_groups.add(str(item.data(_GROUP_ROLE)))

        for index in range(self.list.count()):
            item = self.list.item(index)
            if item.data(_PAGE_ROLE):
                continue
            item.setHidden(str(item.data(_GROUP_ROLE)) not in visible_groups)

        current = self.list.currentItem()
        if current is None or current.isHidden() or not current.data(_PAGE_ROLE):
            self._select_first_visible()

    def _select_first_visible(self) -> None:
        for index in range(self.list.count()):
            item = self.list.item(index)
            if not item.isHidden() and item.data(_PAGE_ROLE):
                self.list.setCurrentItem(item)
                return

    def _current_item_changed(self, current, _previous) -> None:
        if current is None:
            return
        page = current.data(_PAGE_ROLE)
        if page:
            self.page_changed.emit(str(page))
