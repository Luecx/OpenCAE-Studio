"""Provides the ordered hierarchy used by the deck-format manager sidebar."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QStyle,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from opencae.ui.core.icon_factory import IconKind, make_icon

from .catalog import TREE_SPEC


_KEY_ROLE = int(Qt.ItemDataRole.UserRole)
_FIXED_ROLE = _KEY_ROLE + 1
_LABEL_ROLE = _KEY_ROLE + 2


class DeckFormatNavigation(QWidget):
    """Show format records in output order and reorder selected siblings."""

    current_changed = pyqtSignal(str, str)
    order_changed = pyqtSignal()

    def __init__(self, parent=None):
        """Build the searchable two-column tree and movement controls."""
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search records…")
        self.search.setClearButtonEnabled(True)
        root.addWidget(self.search)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(("Record", "Order"))
        self.tree.header().setStretchLastSection(False)
        self.tree.header().resizeSection(1, 52)
        self.tree.setColumnWidth(0, 270)
        self.tree.setRootIsDecorated(True)
        self.tree.setUniformRowHeights(True)
        root.addWidget(self.tree, 1)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(6)
        self.move_up_button = QPushButton("Move Up")
        self.move_up_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp)
        )
        self.move_down_button = QPushButton("Move Down")
        self.move_down_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown)
        )
        buttons.addWidget(self.move_up_button)
        buttons.addWidget(self.move_down_button)
        root.addLayout(buttons)

        self._items: dict[str, QTreeWidgetItem] = {}
        self._populate()
        self.search.textChanged.connect(self._apply_filter)
        self.tree.currentItemChanged.connect(self._selection_changed)
        self.move_up_button.clicked.connect(self.move_up)
        self.move_down_button.clicked.connect(self.move_down)
        self.tree.expandAll()
        self.select_key("materials.isotropic_elastic")

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
        return str(item.data(0, _KEY_ROLE)) if item is not None else ""

    def is_category(self, key: str) -> bool:
        """Return whether ``key`` currently has child records."""
        item = self._items.get(key)
        return bool(item is not None and item.childCount())

    def top_level_labels(self) -> list[str]:
        """Return root labels in their current visual/output order."""
        return [
            str(self.tree.topLevelItem(index).data(0, _LABEL_ROLE))
            for index in range(self.tree.topLevelItemCount())
        ]

    def child_labels(self, key: str) -> list[str]:
        """Return child labels for one category in current order."""
        item = self._items[key]
        return [
            str(item.child(index).data(0, _LABEL_ROLE))
            for index in range(item.childCount())
        ]

    def move_up(self) -> None:
        """Move the selected output record one position up among its siblings."""
        self._move(-1)

    def move_down(self) -> None:
        """Move the selected output record one position down among its siblings."""
        self._move(1)

    def _populate(self) -> None:
        """Populate the tree from the current editor catalog."""
        for node in TREE_SPEC:
            item = self._create_item(node)
            self.tree.addTopLevelItem(item)
            for child in node.get("children", ()):
                item.addChild(self._create_item(child))
        self._refresh_order_numbers()

    def _create_item(self, node: dict) -> QTreeWidgetItem:
        """Create one tree item with stable metadata and a semantic icon."""
        item = QTreeWidgetItem((node["label"], ""))
        item.setData(0, _KEY_ROLE, node["key"])
        item.setData(0, _FIXED_ROLE, bool(node.get("fixed", False)))
        item.setData(0, _LABEL_ROLE, node["label"])
        item.setIcon(0, make_icon(self._icon_kind(node["key"]), 18))
        self._items[node["key"]] = item
        return item

    @staticmethod
    def _icon_kind(key: str) -> IconKind:
        """Map editor record families onto the existing OpenCAE icon language."""
        root = key.split(".", 1)[0]
        return {
            "general": IconKind.SETTINGS,
            "mesh": IconKind.MESH,
            "node_sets": IconKind.NODE_SET,
            "element_sets": IconKind.ELEMENT_SET,
            "surfaces": IconKind.SURFACE,
            "materials": IconKind.MATERIAL,
            "sections": IconKind.SECTION,
            "profiles": IconKind.PROFILE,
            "coordinate_systems": IconKind.CSYS,
            "constraints": IconKind.CONSTRAINT,
            "boundary_conditions": IconKind.SUPPORT,
            "loads": IconKind.LOAD,
            "analysis": IconKind.ANALYSIS,
        }.get(root, IconKind.DECK)

    def _selection_changed(self, current, _previous) -> None:
        """Publish the semantic record selection and refresh movement states."""
        self._refresh_move_buttons()
        if current is None:
            return
        self.current_changed.emit(
            str(current.data(0, _KEY_ROLE)),
            str(current.data(0, _LABEL_ROLE)),
        )

    def _move(self, direction: int) -> None:
        """Move the current item while keeping fixed siblings pinned."""
        item = self.tree.currentItem()
        if item is None or bool(item.data(0, _FIXED_ROLE)):
            return
        parent = item.parent()
        if parent is None:
            index = self.tree.indexOfTopLevelItem(item)
            target = index + direction
            if target < 0 or target >= self.tree.topLevelItemCount():
                return
            destination = self.tree.topLevelItem(target)
            if bool(destination.data(0, _FIXED_ROLE)):
                return
            moved = self.tree.takeTopLevelItem(index)
            self.tree.insertTopLevelItem(target, moved)
        else:
            index = parent.indexOfChild(item)
            target = index + direction
            if target < 0 or target >= parent.childCount():
                return
            destination = parent.child(target)
            if bool(destination.data(0, _FIXED_ROLE)):
                return
            moved = parent.takeChild(index)
            parent.insertChild(target, moved)
            parent.setExpanded(True)
        self.tree.setCurrentItem(item)
        self._refresh_order_numbers()
        self._refresh_move_buttons()
        self.order_changed.emit()

    def _refresh_order_numbers(self) -> None:
        """Show the active sibling order in the dedicated tree column."""
        roots = [
            self.tree.topLevelItem(index)
            for index in range(self.tree.topLevelItemCount())
        ]
        self._number_siblings(roots)
        for root in roots:
            self._number_siblings(
                [root.child(index) for index in range(root.childCount())]
            )

    @staticmethod
    def _number_siblings(items: list[QTreeWidgetItem]) -> None:
        """Number reorderable siblings and leave fixed settings entries blank."""
        order = 1
        for item in items:
            if bool(item.data(0, _FIXED_ROLE)):
                item.setText(1, "")
                continue
            item.setText(1, str(order))
            order += 1

    def _refresh_move_buttons(self) -> None:
        """Enable movement buttons only when the requested move is valid."""
        item = self.tree.currentItem()
        up = down = False
        if item is not None and not bool(item.data(0, _FIXED_ROLE)):
            parent = item.parent()
            if parent is None:
                index = self.tree.indexOfTopLevelItem(item)
                if index > 0:
                    up = not bool(self.tree.topLevelItem(index - 1).data(0, _FIXED_ROLE))
                down = index + 1 < self.tree.topLevelItemCount()
            else:
                index = parent.indexOfChild(item)
                if index > 0:
                    up = not bool(parent.child(index - 1).data(0, _FIXED_ROLE))
                down = index + 1 < parent.childCount()
        self.move_up_button.setEnabled(up)
        self.move_down_button.setEnabled(down)

    def _apply_filter(self, text: str) -> None:
        """Filter leaf labels while keeping matching parent context visible."""
        needle = text.strip().casefold()

        def visit(item: QTreeWidgetItem) -> bool:
            own = needle in str(item.data(0, _LABEL_ROLE)).casefold()
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
