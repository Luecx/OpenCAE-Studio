"""Reusable modeless editor for one Part mesh node."""

from __future__ import annotations

from PyQt6.QtCore import QSignalBlocker, pyqtSignal
from PyQt6.QtWidgets import QDialog, QSpinBox

from opencae.ui.primitives.buttons import SelectionButton
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
    """Edit one stable node ID and global position with viewport picking."""

    picking_changed = pyqtSignal(bool)

    def __init__(
        self,
        node=None,
        *,
        next_id=1,
        details=None,
        parent=None,
    ):
        super().__init__(parent)
        self.node = node
        self.details = dict(details or {})
        self.setWindowTitle("Edit Node" if node is not None else "Create Node")
        self.setMinimumWidth(620)

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

        self.pick_button = SelectionButton(
            "Pick Position in View",
            active_text="Finish Picking",
            tooltip=(
                "Pick a mesh node, geometry vertex, datum point, or reference point"
            ),
            parent=self,
        )
        self.pick_button.toggled.connect(self._pick_toggled)
        root.addWidget(self.pick_button)

        if self.details:
            root.addWidget(SectionHeading("Selection Details"))
            for label, key in (
                ("Incident elements", "incident_elements"),
                ("Regions", "regions"),
                ("CAD associations", "associations"),
                ("Validation", "validation"),
            ):
                if key in self.details:
                    value = self.details.get(key)
                    if isinstance(value, (tuple, list, set)):
                        value = ", ".join(str(item) for item in value) or "—"
                    root.addWidget(field_block(label, ReadOnlyValue(str(value or "—"))))

        root.addStretch(1)
        buttons = dialog_buttons()
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def values(self) -> dict:
        return {
            "node_id": self.node_id.value(),
            "coordinates": self.coordinates.value(),
        }

    def set_coordinates(self, coordinates) -> None:
        self.coordinates.set_value(coordinates)

    def set_picking(self, active: bool) -> None:
        active = bool(active)
        if self.pick_button.isChecked() == active:
            return
        blocker = QSignalBlocker(self.pick_button)
        self.pick_button.setChecked(active)
        del blocker

    def _pick_toggled(self, active: bool) -> None:
        self.picking_changed.emit(bool(active))
