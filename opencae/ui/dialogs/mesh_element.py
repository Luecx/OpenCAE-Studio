"""Provides the reusable create/edit dialog for one finite element."""

from PyQt6.QtWidgets import QDialog, QLineEdit, QMessageBox, QSpinBox

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
    """Collect an element class and ordered connectivity of existing nodes."""

    def __init__(
        self,
        element=None,
        *,
        next_id=1,
        selected_node_ids=(),
        available_node_ids=(),
        parent=None,
    ):
        """Build an editor prefilled from an element or viewport node selection."""
        super().__init__(parent)
        self.element = element
        self.available_node_ids = {int(value) for value in available_node_ids}
        self.setWindowTitle(
            "Edit Element" if element is not None else "Create Element"
        )
        self.setMinimumWidth(620)

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

        values = (
            [node.id for node in element.nodes]
            if element is not None
            else [int(value) for value in selected_node_ids]
        )
        self.connectivity = QLineEdit(", ".join(str(value) for value in values))
        self.connectivity.setPlaceholderText("Ordered node IDs, e.g. 1, 2, 3, 4")
        apply_primary_control_height(self.connectivity)
        root.addWidget(field_block("Connectivity", self.connectivity))
        self.summary = ReadOnlyValue("")
        root.addWidget(field_block("Requirement", self.summary))
        root.addStretch(1)

        self.element_type.currentIndexChanged.connect(self._refresh_summary)
        self._refresh_summary()
        buttons = dialog_buttons()
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def values(self) -> dict:
        """Return element identity, concrete type, and ordered node IDs."""
        return {
            "element_id": self.element_id.value(),
            "element_type": self.element_type.currentData(),
            "node_ids": self._node_ids(),
        }

    def _node_ids(self) -> tuple[int, ...]:
        """Parse comma/space separated positive node IDs."""
        text = self.connectivity.text().replace(",", " ")
        try:
            values = tuple(int(value) for value in text.split())
        except ValueError:
            return ()
        return values if all(value > 0 for value in values) else ()

    def _refresh_summary(self, *_):
        """Show the connectivity cardinality required by the selected class."""
        element_type = self.element_type.currentData()
        count = getattr(element_type, "node_count", None)
        self.summary.set_value(
            f"{count} ordered nodes" if count is not None else "Custom connectivity"
        )

    def _accept(self) -> None:
        """Reject malformed, duplicate, missing, or wrong-sized connectivity."""
        values = self.values()
        node_ids = values["node_ids"]
        expected = getattr(values["element_type"], "node_count", None)
        if not node_ids:
            QMessageBox.warning(self, "Invalid connectivity", "Enter valid node IDs.")
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
                f"{values['element_type'].__name__} requires exactly {expected} nodes.",
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
