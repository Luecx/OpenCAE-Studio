"""Reusable modeless editor for one finite element."""

from __future__ import annotations

from PyQt6.QtCore import QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QSpinBox,
    QToolButton,
    QWidget,
)

from opencae.model.entities.fem import ELEMENT_TYPES
from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.templates import (
    ReadOnlyValue,
    SectionHeading,
    apply_primary_control_height,
    dialog_buttons,
    dialog_layout,
    field_block,
    field_row,
)


class MeshElementDialog(QDialog):
    """Edit element type and ordered connectivity with viewport node picking."""

    picking_changed = pyqtSignal(bool)
    connectivity_changed = pyqtSignal(object)

    def __init__(
        self,
        element=None,
        *,
        next_id=1,
        selected_node_ids=(),
        available_node_ids=(),
        details=None,
        suggested_connectivity=None,
        parent=None,
    ):
        super().__init__(parent)
        self.element = element
        self.details = dict(details or {})
        self.available_node_ids = {int(value) for value in available_node_ids}
        self.suggested_connectivity = (
            tuple(int(value) for value in suggested_connectivity)
            if suggested_connectivity
            else None
        )
        self.setWindowTitle(
            "Edit Element" if element is not None else "Create Element"
        )
        self.setMinimumWidth(680)

        root = dialog_layout(self)
        root.addWidget(SectionHeading("Element Definition"))
        self.element_id = QSpinBox()
        self.element_id.setRange(1, 2_147_483_647)
        self.element_id.setValue(element.id if element is not None else int(next_id))
        self.element_id.setEnabled(element is None)
        apply_primary_control_height(self.element_id)

        self.element_type = ChevronComboBox()
        for value in ELEMENT_TYPES:
            self.element_type.addItem(value.__name__, value)
        current_type = type(element) if element is not None else None
        if current_type in ELEMENT_TYPES:
            self.element_type.setCurrentIndex(ELEMENT_TYPES.index(current_type))
        apply_primary_control_height(self.element_type)
        root.addWidget(
            field_row(
                field_block("Element ID", self.element_id),
                field_block("Element type", self.element_type),
            )
        )

        root.addWidget(SectionHeading("Ordered Connectivity"))
        self.connectivity = QListWidget()
        self.connectivity.setMinimumHeight(180)
        self.connectivity.setAlternatingRowColors(True)
        root.addWidget(self.connectivity)

        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(6)
        self.pick_button = self._button("Pick Nodes", checkable=True)
        self.up_button = self._button("Move Up")
        self.down_button = self._button("Move Down")
        self.remove_button = self._button("Remove")
        self.clear_button = self._button("Clear")
        for button in (
            self.pick_button,
            self.up_button,
            self.down_button,
            self.remove_button,
            self.clear_button,
        ):
            controls_layout.addWidget(button)
        controls_layout.addStretch(1)
        root.addWidget(controls)

        values = (
            [node.id for node in element.nodes]
            if element is not None
            else [int(value) for value in selected_node_ids]
        )
        self.set_node_ids(values, emit=False)

        self.requirement = ReadOnlyValue("")
        root.addWidget(field_block("Requirement", self.requirement))

        if self.details:
            root.addWidget(SectionHeading("Selection Details"))
            for label, key in (
                ("Regions", "regions"),
                ("Section / Material", "sections"),
                ("CAD associations", "associations"),
                ("Validation", "validation"),
            ):
                if key not in self.details:
                    continue
                value = self.details.get(key)
                if isinstance(value, (tuple, list, set)):
                    value = ", ".join(str(item) for item in value) or "—"
                root.addWidget(field_block(label, ReadOnlyValue(str(value or "—"))))

        if self.suggested_connectivity:
            self.repair_button = self._button("Repair Orientation")
            self.repair_button.setToolTip(
                "Apply the conservative node-order flip suggested by validation"
            )
            self.repair_button.clicked.connect(self._apply_orientation_repair)
            root.addWidget(self.repair_button)
        else:
            self.repair_button = None

        root.addStretch(1)
        self.element_type.currentIndexChanged.connect(self._refresh_summary)
        self.pick_button.toggled.connect(self._pick_toggled)
        self.up_button.clicked.connect(lambda: self._move_selected(-1))
        self.down_button.clicked.connect(lambda: self._move_selected(1))
        self.remove_button.clicked.connect(self._remove_selected)
        self.clear_button.clicked.connect(self.clear_nodes)
        self._refresh_summary()

        buttons = dialog_buttons()
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @staticmethod
    def _button(text: str, *, checkable=False) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        button.setCheckable(bool(checkable))
        button.setProperty("inlineAction", True)
        apply_primary_control_height(button)
        return button

    def values(self) -> dict:
        return {
            "element_id": self.element_id.value(),
            "element_type": self.element_type.currentData(),
            "node_ids": self.node_ids(),
        }

    def node_ids(self) -> tuple[int, ...]:
        return tuple(
            int(self.connectivity.item(index).data(Qt.ItemDataRole.UserRole))
            for index in range(self.connectivity.count())
        )

    def set_node_ids(self, values, *, emit=True) -> None:
        self.connectivity.clear()
        for position, node_id in enumerate(values, start=1):
            self._append_item(int(node_id), position)
        if emit:
            self._emit_connectivity()

    def apply_picked_node(self, node_id: int, *, remove=False) -> bool:
        node_id = int(node_id)
        values = list(self.node_ids())
        if remove:
            if node_id not in values:
                return False
            values.remove(node_id)
            self.set_node_ids(values)
            return True
        if node_id in values:
            self.connectivity.setCurrentRow(values.index(node_id))
            return False
        values.append(node_id)
        self.set_node_ids(values)
        self.connectivity.setCurrentRow(len(values) - 1)
        return True

    def clear_nodes(self) -> None:
        if self.connectivity.count():
            self.connectivity.clear()
            self._emit_connectivity()

    def set_picking(self, active: bool) -> None:
        active = bool(active)
        if self.pick_button.isChecked() != active:
            blocker = QSignalBlocker(self.pick_button)
            self.pick_button.setChecked(active)
            del blocker
        self._refresh_pick_text(active)

    def _append_item(self, node_id: int, position: int) -> None:
        item = QListWidgetItem(f"{position}.  Node {node_id}")
        item.setData(Qt.ItemDataRole.UserRole, int(node_id))
        self.connectivity.addItem(item)

    def _move_selected(self, delta: int) -> None:
        row = self.connectivity.currentRow()
        target = row + int(delta)
        if row < 0 or target < 0 or target >= self.connectivity.count():
            return
        values = list(self.node_ids())
        values[row], values[target] = values[target], values[row]
        self.set_node_ids(values)
        self.connectivity.setCurrentRow(target)

    def _remove_selected(self) -> None:
        row = self.connectivity.currentRow()
        if row < 0:
            return
        values = list(self.node_ids())
        del values[row]
        self.set_node_ids(values)
        if values:
            self.connectivity.setCurrentRow(min(row, len(values) - 1))

    def _apply_orientation_repair(self) -> None:
        if not self.suggested_connectivity:
            return
        self.set_node_ids(self.suggested_connectivity)
        if self.repair_button is not None:
            self.repair_button.setEnabled(False)

    def _pick_toggled(self, active: bool) -> None:
        self._refresh_pick_text(active)
        self.picking_changed.emit(bool(active))

    def _refresh_pick_text(self, active: bool) -> None:
        self.pick_button.setText("Finish Picking" if active else "Pick Nodes")

    def _refresh_summary(self, *_):
        element_type = self.element_type.currentData()
        count = getattr(element_type, "node_count", None)
        current = self.connectivity.count()
        self.requirement.set_value(
            f"{current} selected / {count} required"
            if count is not None
            else f"{current} ordered nodes"
        )
        self._emit_connectivity()

    def _emit_connectivity(self) -> None:
        self._renumber_items()
        self.connectivity_changed.emit(
            (self.node_ids(), self.element_type.currentData())
        )
        if hasattr(self, "requirement"):
            element_type = self.element_type.currentData()
            expected = getattr(element_type, "node_count", None)
            current = self.connectivity.count()
            self.requirement.set_value(
                f"{current} selected / {expected} required"
                if expected is not None
                else f"{current} ordered nodes"
            )

    def _renumber_items(self) -> None:
        for index in range(self.connectivity.count()):
            item = self.connectivity.item(index)
            node_id = int(item.data(Qt.ItemDataRole.UserRole))
            item.setText(f"{index + 1}.  Node {node_id}")

    def _accept(self) -> None:
        values = self.values()
        node_ids = values["node_ids"]
        element_type = values["element_type"]
        expected = getattr(element_type, "node_count", None)
        if not node_ids:
            QMessageBox.warning(self, "Invalid connectivity", "Select node IDs first.")
            return
        if len(set(node_ids)) != len(node_ids):
            QMessageBox.warning(
                self,
                "Invalid connectivity",
                "An element cannot use the same node more than once.",
            )
            return
        if expected is not None and len(node_ids) != expected:
            QMessageBox.warning(
                self,
                "Invalid connectivity",
                f"{element_type.__name__} requires exactly {expected} nodes.",
            )
            return
        missing = [value for value in node_ids if value not in self.available_node_ids]
        if missing:
            QMessageBox.warning(
                self,
                "Missing nodes",
                "These node IDs do not exist in the active Part: "
                + ", ".join(str(value) for value in missing),
            )
            return
        self.accept()
