from PyQt6.QtGui import QBrush, QColor, QStandardItem

from opencae.ui.core.theme import PALETTE
from .tree_icons import icon_for
from .tree_roles import ENTITY_ROLE, KIND_ROLE, PART_ROLE

_CHILD_KIND = {
    "instances": "instance", "asm_node_sets": "asm_node_set", "asm_element_sets": "asm_element_set",
    "asm_surfaces": "asm_surface", "asm_coordinate_systems": "asm_coordinate_system",
    "asm_reference_points": "asm_reference_point", "constraints": "constraint",
    "supports": "support", "loads": "load",
}


def item(text, entity=None, kind="item", count=None, is_folder=False, part_id=None):
    label = f"{text}    {count}" if count is not None else text
    node = QStandardItem(icon_for(kind), label); node.setEditable(False)
    node.setData(entity, ENTITY_ROLE); node.setData(kind, KIND_ROLE); node.setData(part_id, PART_ROLE)
    node.setForeground(QBrush(QColor(PALETTE["text"] if entity is not None else PALETTE["muted"])))
    return node


def folder(text, kind="folder", part_id=None):
    return item(text, None, kind, is_folder=True, part_id=part_id)


def ensure_expandable(node, collection, label="Empty"):
    if not collection:
        placeholder = item(label, None, "empty"); placeholder.setEnabled(False); node.appendRow(placeholder)
    return node


def append_collection(parent, title, collection, kind, part_id=None):
    node = folder(title, kind, part_id=part_id); parent.appendRow(node)
    child_kind = _CHILD_KIND.get(kind, kind[:-1] if kind.endswith("s") else kind)
    for entity in collection: node.appendRow(item(entity.name, entity, child_kind, part_id=part_id))
    return ensure_expandable(node, collection)
