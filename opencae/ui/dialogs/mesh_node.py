"""Provides the reusable create/edit dialog for one Part mesh node."""

from PyQt6.QtWidgets import QDialog, QSpinBox

from opencae.ui.templates import (
    ReadOnlyValue,
    SectionHeading,
    Vector3Input,
    apply_primary_control_height,
    dialog_buttons,
    dialog_layout,
    field_block,
    field_row,
)


class MeshNodeDialog(QDialog):
    """Collect a stable node ID and three global coordinates."""

    def __init__(self, node=None, *, next_id=1, parent=None):
        """Build a node editor for creation or coordinate replacement."""
        super().__init__(parent)
        self.node = node
        self.setWindowTitle("Edit Node" if node is not None else "Create Node")
        self.setMinimumWidth(560)

        root = dialog_layout(self)
        root.addWidget(SectionHeading("Node Definition"))
        self.node_id = QSpinBox()
        self.node_id.setRange(1, 2_147_483_647)
        self.node_id.setValue(node.id if node is not None else int(next_id))
        self.node_id.setEnabled(node is None)
        apply_primary_control_height(self.node_id)
        origin = ReadOnlyValue(
            node.origin.value.title() if node is not None else "Authored"
        )
        root.addWidget(
            field_row(
                field_block("Node ID", self.node_id),
                field_block("Origin", origin),
            )
        )
        self.coordinates = Vector3Input(
            node.coordinates if node is not None else (0.0, 0.0, 0.0)
        )
        root.addWidget(field_block("Global coordinates", self.coordinates))
        root.addStretch(1)

        buttons = dialog_buttons()
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def values(self) -> dict:
        """Return the node ID and canonical three-coordinate tuple."""
        return {
            "node_id": self.node_id.value(),
            "coordinates": self.coordinates.value(),
        }
