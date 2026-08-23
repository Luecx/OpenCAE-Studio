"""Build and restore arbitrarily deep deck-format navigation hierarchies."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem

ROOT_ORDER_KEY = "__root__"


def populate_tree(
    tree: QTreeWidget,
    nodes,
    create_item: Callable[[dict], QTreeWidgetItem],
) -> None:
    """Populate ``tree`` recursively from declarative catalog nodes."""
    for node in nodes:
        item = _build_subtree(node, create_item)
        tree.addTopLevelItem(item)


def order_state(tree: QTreeWidget, key_for: Callable[[QTreeWidgetItem], str]) -> dict[str, tuple[str, ...]]:
    """Capture sibling ordering at every hierarchy level by stable item key."""
    roots = [tree.topLevelItem(index) for index in range(tree.topLevelItemCount())]
    state = {ROOT_ORDER_KEY: tuple(key_for(item) for item in roots)}
    for root in roots:
        _capture_children(root, key_for, state)
    return state


def restore_order_state(
    tree: QTreeWidget,
    items: dict[str, QTreeWidgetItem],
    state: dict[str, tuple[str, ...]],
) -> None:
    """Restore every known sibling list without recreating tree items."""
    _reorder_top_level(tree, items, state.get(ROOT_ORDER_KEY, ()))
    for parent_key, keys in state.items():
        if parent_key == ROOT_ORDER_KEY:
            continue
        parent = items.get(parent_key)
        if parent is not None:
            _reorder_children(parent, items, keys)


def _build_subtree(node: dict, create_item) -> QTreeWidgetItem:
    """Create one item and recursively attach all declared descendants."""
    item = create_item(node)
    for child in node.get("children", ()):
        item.addChild(_build_subtree(child, create_item))
    return item


def _capture_children(item, key_for, state) -> None:
    """Capture one child list and recurse into its descendants."""
    if not item.childCount():
        return
    children = [item.child(index) for index in range(item.childCount())]
    state[key_for(item)] = tuple(key_for(child) for child in children)
    for child in children:
        _capture_children(child, key_for, state)


def _reorder_top_level(tree, items, keys) -> None:
    """Reorder existing root items according to ``keys``."""
    for target, key in enumerate(keys):
        item = items.get(key)
        if item is None or item.parent() is not None:
            continue
        current = tree.indexOfTopLevelItem(item)
        if current != target and current >= 0:
            tree.insertTopLevelItem(target, tree.takeTopLevelItem(current))


def _reorder_children(parent, items, keys) -> None:
    """Reorder existing children of one parent according to ``keys``."""
    for target, key in enumerate(keys):
        item = items.get(key)
        if item is None or item.parent() is not parent:
            continue
        current = parent.indexOfChild(item)
        if current != target and current >= 0:
            parent.insertChild(target, parent.takeChild(current))
    parent.setExpanded(True)
