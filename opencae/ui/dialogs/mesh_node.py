"""Reusable modeless editor for one Part mesh node."""

from __future__ import annotations

from PyQt6.QtCore import QSignalBlocker, pyqtSignal
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QMessageBox, QWidget

from opencae.ui.composites.controls import ControlReadOnlyValue, ControlVector3
from opencae.ui.primitives.buttons.button_field_toggle import ButtonFieldToggle
from opencae.ui.primitives.inputs.input_form_integer import InputFormInteger
from opencae.ui.primitives.labels import LabelSection
from opencae.ui.templates import dialog_buttons, dialog_layout, field_block, field_row


class MeshNodeDialog(QDialog):
    """Create or edit one mesh node with independent target/position picking."""

    # ``picking_changed`` remains the compatibility signal for position picking.
    picking_changed = pyqtSignal(bool)
    position_picking_changed = pyqtSignal(bool)
    target_picking_changed = pyqtSignal(bool)
    target_changed = pyqtSignal(object)

    def __init__(
        self,
        node=None,
        *,
        next_id=1,
        details=None,
        editing=None,
        parent=None,
    ):
        super().__init__(parent)
        self.editing = bool(node is not None) if editing is None else bool(editing)
        self.node = node
        self.details = dict(details or {})
        self._target_node_id = int(node.id) if node is not None else None
        self._detail_controls: dict[str, ControlReadOnlyValue] = {}
        self.setWindowTitle("Edit Node" if self.editing else "Create Node")
        self.setMinimumWidth(620)

        root = dialog_layout(self)
        root.addWidget(LabelSection("Node Definition"))

        self.target_value = None
        self.target_pick_button = None
        if self.editing:
            target_row = QWidget(self)
            target_layout = QHBoxLayout(target_row)
            target_layout.setContentsMargins(0, 0, 0, 0)
            target_layout.setSpacing(6)
            self.target_value = ControlReadOnlyValue(
                f"Node {node.id}" if node is not None else "—",
                parent=target_row,
            )
            self.target_pick_button = ButtonFieldToggle(
                "Pick Node",
                tooltip="Pick the mesh node to edit",
                object_name="InlinePickButton",
                parent=target_row,
            )
            target_layout.addWidget(self.target_value, 1)
            target_layout.addWidget(self.target_pick_button)
            root.addWidget(field_block("Node to edit", target_row))

            self.node_id = ControlReadOnlyValue(
                str(node.id) if node is not None else "—"
            )
        else:
            self.node_id = InputFormInteger(
                int(next_id),
                minimum=1,
                maximum=2_147_483_647,
            )

        self.origin = ControlReadOnlyValue(
            node.origin.value.title() if node is not None else "Authored"
        )
        root.addWidget(
            field_row(
                field_block("Node ID", self.node_id),
                field_block("Origin", self.origin),
            )
        )

        self.coordinates = ControlVector3(
            node.coordinates if node is not None else (0.0, 0.0, 0.0)
        )
        root.addWidget(field_block("Global coordinates", self.coordinates))

        self.position_pick_button = ButtonFieldToggle(
            "Pick Position in View",
            tooltip="Pick a mesh node, geometry vertex, datum point, or reference point",
            object_name="InlinePickButton",
            parent=self,
        )
        # Existing callers refer to ``pick_button``/``set_picking``.
        self.pick_button = self.position_pick_button
        root.addWidget(self.position_pick_button)

        if self.editing:
            root.addWidget(LabelSection("Selection Details"))
            for label, key in (
                ("Incident elements", "incident_elements"),
                ("Regions", "regions"),
                ("CAD associations", "associations"),
                ("Validation", "validation"),
            ):
                control = ControlReadOnlyValue("—")
                self._detail_controls[key] = control
                root.addWidget(field_block(label, control))
            self.set_details(self.details)

        self._set_target_dependent_enabled(not self.editing or node is not None)

        self.position_pick_button.toggled.connect(self._position_pick_toggled)
        self.position_pick_button.toggled.connect(self._sync_position_pick_caption)
        if self.target_pick_button is not None:
            self.target_pick_button.toggled.connect(self._target_pick_toggled)
            self.target_pick_button.toggled.connect(self._sync_target_pick_caption)

        root.addStretch(1)
        buttons = dialog_buttons()
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def values(self) -> dict:
        node_id = (
            self._target_node_id
            if self.editing
            else self.node_id.value()
        )
        return {
            "node_id": node_id,
            "coordinates": self.coordinates.value(),
        }

    def set_node(self, node, *, details=None) -> None:
        """Replace the active edit target and load its current state into the form."""
        if not self.editing:
            raise RuntimeError("Node target selection is only available in Edit Node")
        self.node = node
        self._target_node_id = int(node.id)
        if self.target_value is not None:
            self.target_value.set_value(f"Node {node.id}")
        self.node_id.set_value(str(node.id))
        self.origin.set_value(node.origin.value.title())
        self.coordinates.set_value(node.coordinates)
        self.set_details(details or {})
        self._set_target_dependent_enabled(True)
        self.target_changed.emit(node)

    def set_details(self, details) -> None:
        self.details = dict(details or {})
        for key, control in self._detail_controls.items():
            value = self.details.get(key)
            if isinstance(value, (tuple, list, set)):
                value = ", ".join(str(item) for item in value) or "—"
            control.set_value(str(value or "—"))

    def set_coordinates(self, coordinates) -> None:
        self.coordinates.set_value(coordinates)

    def set_position_picking(self, active: bool) -> None:
        active = bool(active)
        if self.position_pick_button.isChecked() != active:
            blocker = QSignalBlocker(self.position_pick_button)
            self.position_pick_button.setChecked(active)
            del blocker
        self._sync_position_pick_caption(active)

    def set_target_picking(self, active: bool) -> None:
        if self.target_pick_button is None:
            return
        active = bool(active)
        if self.target_pick_button.isChecked() != active:
            blocker = QSignalBlocker(self.target_pick_button)
            self.target_pick_button.setChecked(active)
            del blocker
        self._sync_target_pick_caption(active)

    def set_picking(self, active: bool) -> None:
        """Compatibility alias for the position picker."""
        self.set_position_picking(active)

    def _set_target_dependent_enabled(self, enabled: bool) -> None:
        self.coordinates.setEnabled(bool(enabled))
        self.position_pick_button.setEnabled(bool(enabled))

    def _position_pick_toggled(self, active: bool) -> None:
        active = bool(active)
        if active:
            self.set_target_picking(False)
        self.picking_changed.emit(active)
        self.position_picking_changed.emit(active)

    def _target_pick_toggled(self, active: bool) -> None:
        active = bool(active)
        if active:
            self.set_position_picking(False)
        self.target_picking_changed.emit(active)

    def _sync_position_pick_caption(self, active: bool) -> None:
        self.position_pick_button.setText(
            "Finish Picking" if active else "Pick Position in View"
        )

    def _sync_target_pick_caption(self, active: bool) -> None:
        if self.target_pick_button is not None:
            self.target_pick_button.setText(
                "Finish Picking" if active else "Pick Node"
            )

    def _accept(self) -> None:
        if self.editing and self._target_node_id is None:
            QMessageBox.warning(self, "No node selected", "Pick a mesh node to edit first.")
            return
        self.accept()
