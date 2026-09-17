"""Viewport-aware mesh editing extensions for switchable single-node targets."""

from __future__ import annotations

from opencae.model.entities.fem import MeshEntityOrigin, Node
from opencae.model.selection import SelectableKind, SelectionPolicy
from opencae.store.mesh_commands import MoveNodeCommand
from opencae.ui.other.dialogs.mesh_node import MeshNodeDialog
from opencae.ui.other.viewport.mesh_edit_preview import show_position_preview

from .mesh_editing import PartMeshEditing as _BasePartMeshEditing


class InteractivePartMeshEditing(_BasePartMeshEditing):
    """Keep Edit Node modeless while allowing its target to be repicked."""

    def edit_node(self) -> None:
        part = self._part()
        if part is None:
            return

        node_ids = self._selected_ids(SelectableKind.MESH_NODE)
        self._close_existing_dialogs()
        if len(node_ids) > 1:
            self._edit_nodes_bulk(part, node_ids)
            return

        initial = None
        if node_ids:
            try:
                initial = part.mesh.node(node_ids[0])
            except (KeyError, ValueError) as exc:
                self.ctx.error("Edit node failed", exc)
                return

        details = (
            self._node_details(part, initial.id)
            if initial is not None
            else None
        )
        dialog = MeshNodeDialog(
            initial,
            editing=True,
            details=details,
            parent=self.ctx.parent,
        )
        part_id = part.id
        dialog.accepted.connect(
            lambda: self._commit_edited_node(part_id, dialog)
        )
        self._connect_node_picking(dialog, part_id)
        self._track(dialog, clear_preview=True)

        viewport = self._viewport()
        if initial is not None:
            show_position_preview(viewport, initial.coordinates)
        else:
            dialog.set_target_picking(True)

    def _commit_edited_node(self, part_id, dialog) -> None:
        part = self._live_part(part_id)
        if part is None:
            return
        values = dialog.values()
        node_id = values.get("node_id")
        if node_id is None:
            self.ctx.store.message.emit("Pick a mesh node to edit first")
            return
        try:
            current = part.mesh.node(int(node_id))
        except (KeyError, ValueError) as exc:
            self.ctx.error("Edit node failed", exc)
            return

        after = Node(
            current.id,
            values["coordinates"],
            MeshEntityOrigin.AUTHORED,
        )
        if after.coordinates == current.coordinates:
            return
        self._execute(
            f"Moved node {current.id}",
            MoveNodeCommand(part.id, current, after),
            part.id,
        )

    def _connect_node_picking(self, dialog, part_id=None) -> None:
        """Wire independent target-node and position pick sessions."""
        viewport = self._viewport()
        if viewport is None:
            dialog.position_pick_button.setEnabled(False)
            if dialog.target_pick_button is not None:
                dialog.target_pick_button.setEnabled(False)
            return

        def position_toggle(active):
            if not active:
                viewport.cancel_context_pick()
                return
            viewport.cancel_context_pick()
            policy = SelectionPolicy.create(
                {
                    SelectableKind.MESH_NODE,
                    SelectableKind.GEOMETRY_VERTEX,
                    SelectableKind.REFERENCE_POINT,
                    SelectableKind.DATUM_POINT,
                },
                multiple=False,
            )

            def selected(hit):
                if hit.world_position is None:
                    self.ctx.store.message.emit(
                        "The selected object has no usable world position"
                    )
                    return
                dialog.set_coordinates(hit.world_position)
                show_position_preview(viewport, hit.world_position)

            viewport.begin_selection_session(
                policy,
                selected,
                finished=lambda: dialog.set_position_picking(False),
            )

        dialog.position_picking_changed.connect(position_toggle)
        dialog.coordinates.changed.connect(
            lambda: show_position_preview(viewport, dialog.coordinates.value())
        )

        if dialog.target_pick_button is None or part_id is None:
            return

        def target_toggle(active):
            if not active:
                viewport.cancel_context_pick()
                return
            viewport.cancel_context_pick()
            viewport.set_display_mode("mesh")
            policy = SelectionPolicy.create(
                {SelectableKind.MESH_NODE},
                multiple=False,
            )

            def selected(hit):
                if hit.mesh_id is None:
                    return
                live_part = self._live_part(part_id, quiet=True)
                if live_part is None:
                    return
                try:
                    node = live_part.mesh.node(int(hit.mesh_id))
                except (KeyError, ValueError):
                    self.ctx.store.message.emit("The picked mesh node no longer exists")
                    return
                dialog.set_node(
                    node,
                    details=self._node_details(live_part, node.id),
                )
                show_position_preview(viewport, node.coordinates)

            viewport.begin_selection_session(
                policy,
                selected,
                finished=lambda: dialog.set_target_picking(False),
            )

        dialog.target_picking_changed.connect(target_toggle)
