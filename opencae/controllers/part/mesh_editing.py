"""Coordinates individual node and element editing for the active Part mesh."""

from PyQt6.QtWidgets import QDialog, QMessageBox

from opencae.model.entities.fem import MeshEntityOrigin, Node
from opencae.model.selection import SelectableKind, ViewportSelection
from opencae.store.mesh_commands import (
    CreateElementCommand,
    CreateNodeCommand,
    DeleteElementCommand,
    DeleteNodeCommand,
    MoveNodeCommand,
    ReplaceElementCommand,
)
from opencae.ui.dialogs.mesh_element import MeshElementDialog
from opencae.ui.dialogs.mesh_node import MeshNodeDialog


class PartMeshEditing:
    """Expose undoable single-entity mesh operations to UI actions."""

    def __init__(self, context):
        """Retain the shared Part controller context."""
        self.ctx = context

    def create_node(self) -> None:
        """Create one free node in the active Part."""
        part = self._part()
        if part is None:
            return
        dialog = MeshNodeDialog(
            next_id=part.mesh.nodes.next_id(),
            parent=self.ctx.parent,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        node = Node(
            values["node_id"],
            values["coordinates"],
            MeshEntityOrigin.AUTHORED,
        )
        self._execute(
            f"Created node {node.id}",
            CreateNodeCommand(part.id, node),
        )

    def edit_node(self) -> None:
        """Move the one mesh node currently selected in the viewport."""
        part = self._part()
        node_id = self._single_selected_id(SelectableKind.MESH_NODE, "node")
        if part is None or node_id is None:
            return
        try:
            before = part.mesh.node(node_id)
        except (KeyError, ValueError) as exc:
            self.ctx.error("Edit node failed", exc)
            return
        dialog = MeshNodeDialog(before, parent=self.ctx.parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        after = Node(
            before.id,
            dialog.values()["coordinates"],
            MeshEntityOrigin.AUTHORED,
        )
        if after.coordinates == before.coordinates:
            return
        self._execute(
            f"Moved node {before.id}",
            MoveNodeCommand(part.id, before, after),
        )

    def delete_node(self) -> None:
        """Delete one selected unused node after explicit confirmation."""
        part = self._part()
        node_id = self._single_selected_id(SelectableKind.MESH_NODE, "node")
        if part is None or node_id is None:
            return
        try:
            node = part.mesh.node(node_id)
        except (KeyError, ValueError) as exc:
            self.ctx.error("Delete node failed", exc)
            return
        if QMessageBox.question(
            self.ctx.parent,
            "Delete Node",
            f"Delete node {node.id}? Connected nodes must be reconnected first.",
        ) != QMessageBox.StandardButton.Yes:
            return
        self._execute(
            f"Deleted node {node.id}",
            DeleteNodeCommand(part.id, node),
        )

    def create_element(self) -> None:
        """Create one free element from existing nodes in the active Part."""
        part = self._part()
        if part is None:
            return
        dialog = MeshElementDialog(
            next_id=part.mesh.next_element_id(),
            selected_node_ids=self._selected_ids(SelectableKind.MESH_NODE),
            available_node_ids=part.mesh.nodes.ids,
            parent=self.ctx.parent,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            nodes = tuple(part.mesh.node(value) for value in values["node_ids"])
            element = values["element_type"](
                values["element_id"],
                nodes,
                MeshEntityOrigin.AUTHORED,
            )
        except (KeyError, TypeError, ValueError) as exc:
            self.ctx.error("Create element failed", exc)
            return
        self._execute(
            f"Created element {element.id}",
            CreateElementCommand(part.id, element),
        )

    def edit_element(self) -> None:
        """Edit type and ordered connectivity of one selected element."""
        part = self._part()
        element_id = self._single_selected_id(
            SelectableKind.MESH_ELEMENT,
            "element",
        )
        if part is None or element_id is None:
            return
        try:
            before = part.mesh.element(element_id)
        except (KeyError, ValueError) as exc:
            self.ctx.error("Edit element failed", exc)
            return
        dialog = MeshElementDialog(
            before,
            available_node_ids=part.mesh.nodes.ids,
            parent=self.ctx.parent,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            nodes = tuple(part.mesh.node(value) for value in values["node_ids"])
            after = values["element_type"](
                before.id,
                nodes,
                MeshEntityOrigin.AUTHORED,
            )
        except (KeyError, TypeError, ValueError) as exc:
            self.ctx.error("Edit element failed", exc)
            return
        if type(after) is type(before) and after.connectivity == before.connectivity:
            return
        self._execute(
            f"Edited element {before.id}",
            ReplaceElementCommand(part.id, before, after),
        )

    def delete_element(self) -> None:
        """Delete one selected element after explicit confirmation."""
        part = self._part()
        element_id = self._single_selected_id(
            SelectableKind.MESH_ELEMENT,
            "element",
        )
        if part is None or element_id is None:
            return
        try:
            element = part.mesh.element(element_id)
        except (KeyError, ValueError) as exc:
            self.ctx.error("Delete element failed", exc)
            return
        if QMessageBox.question(
            self.ctx.parent,
            "Delete Element",
            f"Delete element {element.id}? Direct region memberships will be removed.",
        ) != QMessageBox.StandardButton.Yes:
            return
        self._execute(
            f"Deleted element {element.id}",
            DeleteElementCommand(part.id, element),
        )

    def _part(self):
        """Return the active Part or publish one actionable UI message."""
        part = self.ctx.active_part()
        if part is None:
            self.ctx.store.message.emit("Create or activate a Part first")
        return part

    def _selected_ids(self, kind: SelectableKind) -> tuple[int, ...]:
        """Return unique mesh IDs of one kind from transient viewport selection."""
        selection = self.ctx.store.selection
        if not isinstance(selection, ViewportSelection):
            return ()
        result = []
        for hit in selection.hits:
            if hit.kind is kind and hit.mesh_id is not None:
                value = int(hit.mesh_id)
                if value not in result:
                    result.append(value)
        return tuple(result)

    def _single_selected_id(self, kind: SelectableKind, label: str) -> int | None:
        """Require exactly one viewport-selected node or element."""
        values = self._selected_ids(kind)
        if len(values) != 1:
            self.ctx.store.message.emit(
                f"Select exactly one mesh {label} in the viewport first"
            )
            return None
        return values[0]

    def _execute(self, description, command) -> bool:
        """Run one mesh command and refresh the mesh viewport on success."""
        try:
            self.ctx.store.execute(description, command)
        except (KeyError, TypeError, ValueError) as exc:
            self.ctx.error("Mesh edit failed", exc)
            return False
        self.ctx.store.invalidate_scene(description)
        viewport = getattr(self.ctx.parent, "viewport", None)
        if viewport is not None:
            viewport.set_display_mode("mesh")
        return True
