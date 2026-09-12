"""Bulk node and element editors for viewport multi-selection."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHeaderView,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
)

from opencae.model.entities.fem import ELEMENT_TYPES
from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.templates import (
    ReadOnlyValue,
    SectionHeading,
    Vector3Input,
    apply_primary_control_height,
    dialog_buttons,
    dialog_layout,
    field_block,
)


class MeshNodeBulkDialog(QDialog):
    """Edit coordinates of several nodes and optionally translate them together."""

    def __init__(self, nodes, parent=None):
        super().__init__(parent)
        self.nodes = tuple(nodes)
        self.setWindowTitle(f"Edit {len(self.nodes)} Nodes")
        self.setMinimumWidth(760)
        root = dialog_layout(self)
        root.addWidget(SectionHeading("Selected Nodes"))
        self.table = QTableWidget(len(self.nodes), 5)
        self.table.setHorizontalHeaderLabels(("ID", "X", "Y", "Z", "Origin"))
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        for row, node in enumerate(self.nodes):
            self._readonly(row, 0, str(node.id))
            for column, value in enumerate(node.coordinates, start=1):
                self.table.setItem(row, column, QTableWidgetItem(f"{float(value):.12g}"))
            self._readonly(row, 4, node.origin.value.title())
        root.addWidget(self.table)
        root.addWidget(SectionHeading("Bulk Translation"))
        self.translation = Vector3Input((0.0, 0.0, 0.0), labels=("dX", "dY", "dZ"))
        root.addWidget(field_block("Offset added to every row", self.translation))
        root.addWidget(
            field_block(
                "Selection",
                ReadOnlyValue(f"{len(self.nodes)} node(s)"),
            )
        )
        root.addStretch(1)
        buttons = dialog_buttons()
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def values(self) -> dict[int, tuple[float, float, float]]:
        delta = self.translation.value()
        result = {}
        for row, node in enumerate(self.nodes):
            base = tuple(float(self.table.item(row, column).text()) for column in (1, 2, 3))
            result[node.id] = tuple(base[index] + delta[index] for index in range(3))
        return result

    def _accept(self) -> None:
        try:
            self.values()
        except (AttributeError, TypeError, ValueError):
            QMessageBox.warning(
                self,
                "Invalid coordinates",
                "Every X/Y/Z cell must contain a valid number.",
            )
            return
        self.accept()

    def _readonly(self, row, column, text) -> None:
        item = QTableWidgetItem(str(text))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, column, item)


class MeshElementBulkDialog(QDialog):
    """Bulk-edit element connectivity and optionally apply one common type."""

    def __init__(self, elements, *, available_node_ids=(), parent=None):
        super().__init__(parent)
        self.elements = tuple(elements)
        self.available_node_ids = {int(value) for value in available_node_ids}
        self.setWindowTitle(f"Edit {len(self.elements)} Elements")
        self.setMinimumWidth(840)
        root = dialog_layout(self)
        root.addWidget(SectionHeading("Bulk Type Change"))
        self.element_type = ChevronComboBox()
        self.element_type.addItem("Keep current types", None)
        for value in ELEMENT_TYPES:
            self.element_type.addItem(value.__name__, value)
        apply_primary_control_height(self.element_type)
        root.addWidget(field_block("Apply type to all selected elements", self.element_type))

        root.addWidget(SectionHeading("Selected Elements"))
        self.table = QTableWidget(len(self.elements), 4)
        self.table.setHorizontalHeaderLabels(("ID", "Type", "Connectivity", "Origin"))
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        for row, element in enumerate(self.elements):
            self._readonly(row, 0, str(element.id))
            self._readonly(row, 1, type(element).__name__)
            self.table.setItem(
                row,
                2,
                QTableWidgetItem(", ".join(str(value) for value in element.connectivity)),
            )
            self._readonly(row, 3, element.origin.value.title())
        root.addWidget(self.table)
        root.addWidget(
            field_block(
                "Selection",
                ReadOnlyValue(f"{len(self.elements)} element(s)"),
            )
        )
        root.addStretch(1)
        buttons = dialog_buttons()
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def values(self) -> tuple[dict, ...]:
        common_type = self.element_type.currentData()
        result = []
        for row, element in enumerate(self.elements):
            text = self.table.item(row, 2).text().replace(",", " ")
            node_ids = tuple(int(value) for value in text.split())
            result.append(
                {
                    "element_id": element.id,
                    "element_type": common_type or type(element),
                    "node_ids": node_ids,
                }
            )
        return tuple(result)

    def _accept(self) -> None:
        try:
            values = self.values()
        except (AttributeError, TypeError, ValueError):
            QMessageBox.warning(
                self,
                "Invalid connectivity",
                "Every connectivity cell must contain integer node IDs.",
            )
            return
        problems = []
        for value in values:
            node_ids = value["node_ids"]
            element_type = value["element_type"]
            expected = getattr(element_type, "node_count", None)
            if not node_ids or any(node_id <= 0 for node_id in node_ids):
                problems.append(f"Element {value['element_id']}: invalid node IDs")
            elif len(set(node_ids)) != len(node_ids):
                problems.append(f"Element {value['element_id']}: duplicate node IDs")
            elif expected is not None and len(node_ids) != expected:
                problems.append(
                    f"Element {value['element_id']}: {element_type.__name__} needs {expected} nodes"
                )
            else:
                missing = [node_id for node_id in node_ids if node_id not in self.available_node_ids]
                if missing:
                    problems.append(
                        f"Element {value['element_id']}: missing "
                        + ", ".join(str(node_id) for node_id in missing)
                    )
        if problems:
            QMessageBox.warning(
                self,
                "Invalid connectivity",
                "\n".join(problems[:12]),
            )
            return
        self.accept()

    def _readonly(self, row, column, text) -> None:
        item = QTableWidgetItem(str(text))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, column, item)
