"""Provides the ordered hierarchy used by the deck-format manager sidebar."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QStyle, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from opencae.ui.core.fields import FieldSpec, create_editor
from opencae.ui.core.icon_factory import make_icon
from opencae.ui.templates import ButtonSpec, apply_primary_control_height, button

from .catalog import TREE_SPEC
from .navigation_icons import deck_record_icon_kind
from .navigation_tree import order_state, populate_tree, restore_order_state


_KEY_ROLE = int(Qt.ItemDataRole.UserRole)
_FIXED_ROLE = _KEY_ROLE + 1


class DeckFormatNavigation(QWidget):
    """Show format records in output order and reorder selected siblings."""

    current_changed = pyqtSignal(str, str)
    order_changed = pyqtSignal()

    def __init__(self, parent=None):
        """Build the searchable hierarchy and canonical movement controls."""
        super().__init__(parent)
        self._editable = True
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        search = create_editor(FieldSpec("search", "Search"))
        if not isinstance(search, QLineEdit):
            raise TypeError("Deck navigation search must use QLineEdit")
        self.search = search
        self.search.setPlaceholderText("Search records…")
        self.search.setClearButtonEnabled(True)
        root.addWidget(self.search)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setUniformRowHeights(True)
        root.addWidget(self.tree, 1)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(6)
        self.move_up_button = self._move_button("Move Up", QStyle.StandardPixmap.SP_ArrowUp, self.move_up)
        self.move_down_button = self._move_button("Move Down", QStyle.StandardPixmap.SP_ArrowDown, self.move_down)
        controls.addWidget(self.move_up_button)
        controls.addWidget(self.move_down_button)
        root.addLayout(controls)

        self._items: dict[str, QTreeWidgetItem] = {}
        populate_tree(self.tree, TREE_SPEC, self._create_item)
        self.search.textChanged.connect(self._apply_filter)
        self.tree.currentItemChanged.connect(self._selection_changed)
        self.tree.expandAll()
        self._refresh_move_buttons()

    def select_key(self, key: str) -> bool:
        """Select a known record key and return whether it exists."""
        item = self._items.get(key)
        if item is None:
            return False
        self.tree.setCurrentItem(item)
        self.tree.scrollToItem(item)
        return True

    def current_key(self) -> str:
        """Return the stable key for the current navigation item."""
        item = self.tree.currentItem()
        return self._key(item) if item is not None else ""

    def is_category(self, key: str) -> bool:
        """Return whether ``key`` currently has child records."""
        item = self._items.get(key)
        return bool(item is not None and item.childCount())

    def set_editable(self, editable: bool) -> None:
        """Enable or disable ordering without disabling tree navigation."""
        self._editable = bool(editable)
        self._refresh_move_buttons()

    def top_level_labels(self) -> list[str]:
        """Return root labels in their current visual/output order."""
        return [self.tree.topLevelItem(index).text(0) for index in range(self.tree.topLevelItemCount())]

    def child_labels(self, key: str) -> list[str]:
        """Return direct child labels for one category in current order."""
        item = self._items[key]
        return [item.child(index).text(0) for index in range(item.childCount())]

    def order_state(self) -> dict[str, tuple[str, ...]]:
        """Return stable sibling-key ordering for every hierarchy level."""
        return order_state(self.tree, self._key)

    def set_order_state(self, state: dict[str, tuple[str, ...]]) -> None:
        """Restore sibling ordering by stable record keys without emitting edits."""
        restore_order_state(self.tree, self._items, state)
        self._refresh_move_buttons()

    def move_up(self) -> None:
        """Move the selected output record one position up among its siblings."""
        self._move(-1)

    def move_down(self) -> None:
        """Move the selected output record one position down among its siblings."""
        self._move(1)

    def _move_button(self, text, pixmap, callback):
        """Create a canonical primary-height navigation action."""
        control = button(ButtonSpec(text, icon=self.style().standardIcon(pixmap)), clicked=callback)
        return apply_primary_control_height(control)

    def _create_item(self, node: dict) -> QTreeWidgetItem:
        """Create one tree item with stable metadata and a semantic icon."""
        item = QTreeWidgetItem((node["label"],))
        item.setData(0, _KEY_ROLE, node["key"])
        item.setData(0, _FIXED_ROLE, bool(node.get("fixed", False)))
        item.setIcon(0, make_icon(deck_record_icon_kind(node["key"]), 18))
        self._items[node["key"]] = item
        return item

    @staticmethod
    def _key(item: QTreeWidgetItem) -> str:
        """Return one item's stable catalog key."""
        return str(item.data(0, _KEY_ROLE))

    def _selection_changed(self, current, _previous) -> None:
        """Publish the semantic record selection and refresh movement states."""
        self._refresh_move_buttons()
        if current is not None:
            self.current_changed.emit(self._key(current), current.text(0))

    def _move(self, direction: int) -> None:
        """Move the current item while keeping fixed siblings pinned."""
        item = self.tree.currentItem()
        if not self._editable or item is None or bool(item.data(0, _FIXED_ROLE)):
            return
        parent = item.parent()
        if parent is None:
            index = self.tree.indexOfTopLevelItem(item)
            target = index + direction
            if not 0 <= target < self.tree.topLevelItemCount():
                return
            if bool(self.tree.topLevelItem(target).data(0, _FIXED_ROLE)):
                return
            moved = self.tree.takeTopLevelItem(index)
            self.tree.insertTopLevelItem(target, moved)
        else:
            index = parent.indexOfChild(item)
            target = index + direction
            if not 0 <= target < parent.childCount():
                return
            if bool(parent.child(target).data(0, _FIXED_ROLE)):
                return
            moved = parent.takeChild(index)
            parent.insertChild(target, moved)
            parent.setExpanded(True)
        self.tree.setCurrentItem(item)
        self._refresh_move_buttons()
        self.order_changed.emit()

    def _refresh_move_buttons(self) -> None:
        """Enable movement buttons only when the requested move is valid."""
        item = self.tree.currentItem()
        up = down = False
        if self._editable and item is not None and not bool(item.data(0, _FIXED_ROLE)):
            parent = item.parent()
            if parent is None:
                index = self.tree.indexOfTopLevelItem(item)
                up = index > 0 and not bool(self.tree.topLevelItem(index - 1).data(0, _FIXED_ROLE))
                down = index + 1 < self.tree.topLevelItemCount()
            else:
                index = parent.indexOfChild(item)
                up = index > 0 and not bool(parent.child(index - 1).data(0, _FIXED_ROLE))
                down = index + 1 < parent.childCount()
        self.move_up_button.setEnabled(up)
        self.move_down_button.setEnabled(down)

    def _apply_filter(self, text: str) -> None:
        """Filter descendants while keeping matching ancestor context visible."""
        needle = text.strip().casefold()

        def visit(item: QTreeWidgetItem) -> bool:
            own = needle in item.text(0).casefold()
            child_match = False
            for index in range(item.childCount()):
                child_match = visit(item.child(index)) or child_match
            visible = not needle or own or child_match
            item.setHidden(not visible)
            if needle and child_match:
                item.setExpanded(True)
            return visible

        for index in range(self.tree.topLevelItemCount()):
            visit(self.tree.topLevelItem(index))
