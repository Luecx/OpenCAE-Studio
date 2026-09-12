"""Interactive single- and multi-entity editing for the active Part mesh."""

from __future__ import annotations

from PyQt6.QtWidgets import QMessageBox

from opencae.model.entities.fem import MeshEntityOrigin, Node
from opencae.model.entities.mesh import (
    suggested_orientation_repair,
    validate_element,
    validate_node_move,
)
from opencae.model.selection import (
    RegionProjection,
    RegionRequirement,
    RegionResolver,
    SelectableKind,
    SelectionOperation,
    SelectionPolicy,
    ViewportSelection,
)
from opencae.store.commands import CompositeCommand
from opencae.store.mesh_commands import (
    CreateElementCommand,
    CreateNodeCommand,
    DeleteElementCommand,
    DeleteNodeCommand,
    MoveNodeCommand,
    ReplaceElementCommand,
)
from opencae.ui.core.dialog_lifecycle import show_modeless_dialog
from opencae.ui.dialogs.mesh_bulk import (
    MeshElementBulkDialog,
    MeshNodeBulkDialog,
)
from opencae.ui.dialogs.mesh_element import MeshElementDialog
from opencae.ui.dialogs.mesh_node import MeshNodeDialog
from opencae.ui.viewport.mesh_edit_preview import (
    clear_mesh_edit_preview,
    show_connectivity_preview,
    show_position_preview,
)


class PartMeshEditing:
    """Expose undoable mesh editing while keeping picking strictly transient."""

    def __init__(self, context):
        self.ctx = context
        self._dialogs = []

    def create_node(self) -> None:
        part = self._part()
        if part is None:
            return
        self._close_existing_dialogs()
        dialog = MeshNodeDialog(
            next_id=part.mesh.nodes.next_id(),
            parent=self.ctx.parent,
        )
        part_id = part.id
        dialog.accepted.connect(lambda: self._commit_created_node(part_id, dialog))
        self._connect_node_picking(dialog)
        self._track(dialog, clear_preview=True)
        show_position_preview(self._viewport(), dialog.coordinates.value())

    def edit_node(self) -> None:
        part = self._part()
        if part is None:
            return
        node_ids = self._selected_ids(SelectableKind.MESH_NODE)
        if not node_ids:
            self.ctx.store.message.emit("Select one or more mesh nodes first")
            return
        self._close_existing_dialogs()
        if len(node_ids) > 1:
            self._edit_nodes_bulk(part, node_ids)
            return
        node_id = node_ids[0]
        try:
            before = part.mesh.node(node_id)
        except (KeyError, ValueError) as exc:
            self.ctx.error("Edit node failed", exc)
            return
        dialog = MeshNodeDialog(
            before,
            details=self._node_details(part, node_id),
            parent=self.ctx.parent,
        )
        part_id = part.id
        dialog.accepted.connect(
            lambda: self._commit_edited_node(part_id, before, dialog)
        )
        self._connect_node_picking(dialog)
        self._track(dialog, clear_preview=True)
        show_position_preview(self._viewport(), before.coordinates)

    def delete_node(self) -> None:
        part = self._part()
        if part is None:
            return
        node_ids = self._selected_ids(SelectableKind.MESH_NODE)
        if not node_ids:
            self.ctx.store.message.emit("Select one or more mesh nodes first")
            return
        nodes = []
        connected = set()
        try:
            for node_id in node_ids:
                nodes.append(part.mesh.node(node_id))
                connected.update(part.mesh.incident_element_ids(node_id))
        except (KeyError, ValueError) as exc:
            self.ctx.error("Delete node failed", exc)
            return
        detail = (
            f" This also deletes {len(connected)} connected element(s)."
            if connected
            else ""
        )
        if QMessageBox.question(
            self.ctx.parent,
            "Delete Nodes" if len(nodes) > 1 else "Delete Node",
            f"Delete {len(nodes)} selected node(s)?{detail}",
        ) != QMessageBox.StandardButton.Yes:
            return
        commands = []
        for element_id in sorted(connected):
            commands.append(
                DeleteElementCommand(part.id, part.mesh.element(element_id))
            )
        commands.extend(DeleteNodeCommand(part.id, node) for node in nodes)
        self._execute(
            f"Deleted {len(nodes)} node(s)",
            self._command(commands),
            part.id,
        )

    def create_element(self) -> None:
        part = self._part()
        if part is None:
            return
        self._close_existing_dialogs()
        dialog = MeshElementDialog(
            next_id=part.mesh.next_element_id(),
            selected_node_ids=self._selected_ids(SelectableKind.MESH_NODE),
            available_node_ids=part.mesh.nodes.ids,
            parent=self.ctx.parent,
        )
        part_id = part.id
        dialog.accepted.connect(
            lambda: self._commit_created_element(part_id, dialog)
        )
        self._connect_element_picking(dialog, part_id)
        self._track(dialog, clear_preview=True)
        self._preview_dialog_connectivity(part_id, dialog)

    def edit_element(self) -> None:
        part = self._part()
        if part is None:
            return
        element_ids = self._selected_ids(SelectableKind.MESH_ELEMENT)
        if not element_ids:
            self.ctx.store.message.emit("Select one or more mesh elements first")
            return
        self._close_existing_dialogs()
        if len(element_ids) > 1:
            self._edit_elements_bulk(part, element_ids)
            return
        element_id = element_ids[0]
        try:
            before = part.mesh.element(element_id)
        except (KeyError, ValueError) as exc:
            self.ctx.error("Edit element failed", exc)
            return
        repair = suggested_orientation_repair(before)
        dialog = MeshElementDialog(
            before,
            available_node_ids=part.mesh.nodes.ids,
            details=self._element_details(part, before),
            suggested_connectivity=repair,
            parent=self.ctx.parent,
        )
        part_id = part.id
        dialog.accepted.connect(
            lambda: self._commit_edited_element(part_id, before, dialog)
        )
        self._connect_element_picking(dialog, part_id)
        self._track(dialog, clear_preview=True)
        self._preview_dialog_connectivity(part_id, dialog)

    def delete_element(self) -> None:
        part = self._part()
        if part is None:
            return
        element_ids = self._selected_ids(SelectableKind.MESH_ELEMENT)
        if not element_ids:
            self.ctx.store.message.emit("Select one or more mesh elements first")
            return
        try:
            elements = [part.mesh.element(value) for value in element_ids]
        except (KeyError, ValueError) as exc:
            self.ctx.error("Delete element failed", exc)
            return
        if QMessageBox.question(
            self.ctx.parent,
            "Delete Elements" if len(elements) > 1 else "Delete Element",
            f"Delete {len(elements)} selected element(s)? Direct region memberships will be removed.",
        ) != QMessageBox.StandardButton.Yes:
            return
        self._execute(
            f"Deleted {len(elements)} element(s)",
            self._command(
                [DeleteElementCommand(part.id, value) for value in elements]
            ),
            part.id,
        )

    def _edit_nodes_bulk(self, part, node_ids) -> None:
        try:
            nodes = tuple(part.mesh.node(value) for value in node_ids)
        except (KeyError, ValueError) as exc:
            self.ctx.error("Edit nodes failed", exc)
            return
        dialog = MeshNodeBulkDialog(nodes, parent=self.ctx.parent)
        part_id = part.id
        dialog.accepted.connect(
            lambda: self._commit_bulk_nodes(part_id, nodes, dialog)
        )
        self._track(dialog)

    def _edit_elements_bulk(self, part, element_ids) -> None:
        try:
            elements = tuple(part.mesh.element(value) for value in element_ids)
        except (KeyError, ValueError) as exc:
            self.ctx.error("Edit elements failed", exc)
            return
        dialog = MeshElementBulkDialog(
            elements,
            available_node_ids=part.mesh.nodes.ids,
            parent=self.ctx.parent,
        )
        part_id = part.id
        dialog.accepted.connect(
            lambda: self._commit_bulk_elements(part_id, elements, dialog)
        )
        self._track(dialog)

    def _commit_created_node(self, part_id, dialog) -> None:
        part = self._live_part(part_id)
        if part is None:
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
            part.id,
        )

    def _commit_edited_node(self, part_id, before, dialog) -> None:
        part = self._live_part(part_id)
        if part is None:
            return
        try:
            current = part.mesh.node(before.id)
        except (KeyError, ValueError) as exc:
            self.ctx.error("Edit node failed", exc)
            return
        after = Node(
            current.id,
            dialog.values()["coordinates"],
            MeshEntityOrigin.AUTHORED,
        )
        if after.coordinates == current.coordinates:
            return
        self._execute(
            f"Moved node {current.id}",
            MoveNodeCommand(part.id, current, after),
            part.id,
        )

    def _commit_bulk_nodes(self, part_id, originals, dialog) -> None:
        part = self._live_part(part_id)
        if part is None:
            return
        values = dialog.values()
        commands = []
        for original in originals:
            current = part.mesh.node(original.id)
            coordinates = values[original.id]
            if current.coordinates == coordinates:
                continue
            after = Node(current.id, coordinates, MeshEntityOrigin.AUTHORED)
            commands.append(MoveNodeCommand(part.id, current, after))
        if commands:
            self._execute(
                f"Moved {len(commands)} node(s)",
                self._command(commands),
                part.id,
            )

    def _commit_created_element(self, part_id, dialog) -> None:
        part = self._live_part(part_id)
        if part is None:
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
            part.id,
        )

    def _commit_edited_element(self, part_id, before, dialog) -> None:
        part = self._live_part(part_id)
        if part is None:
            return
        try:
            current = part.mesh.element(before.id)
            values = dialog.values()
            nodes = tuple(part.mesh.node(value) for value in values["node_ids"])
            after = values["element_type"](
                current.id,
                nodes,
                MeshEntityOrigin.AUTHORED,
            )
        except (KeyError, TypeError, ValueError) as exc:
            self.ctx.error("Edit element failed", exc)
            return
        if type(after) is type(current) and after.connectivity == current.connectivity:
            return
        self._execute(
            f"Edited element {current.id}",
            ReplaceElementCommand(part.id, current, after),
            part.id,
        )

    def _commit_bulk_elements(self, part_id, originals, dialog) -> None:
        part = self._live_part(part_id)
        if part is None:
            return
        commands = []
        try:
            for value in dialog.values():
                current = part.mesh.element(value["element_id"])
                nodes = tuple(part.mesh.node(node_id) for node_id in value["node_ids"])
                after = value["element_type"](
                    current.id,
                    nodes,
                    MeshEntityOrigin.AUTHORED,
                )
                if type(after) is type(current) and after.connectivity == current.connectivity:
                    continue
                commands.append(ReplaceElementCommand(part.id, current, after))
        except (KeyError, TypeError, ValueError) as exc:
            self.ctx.error("Edit elements failed", exc)
            return
        if commands:
            self._execute(
                f"Edited {len(commands)} element(s)",
                self._command(commands),
                part.id,
            )

    def _connect_node_picking(self, dialog) -> None:
        viewport = self._viewport()
        if viewport is None:
            dialog.pick_button.setEnabled(False)
            return

        def toggle(active):
            if not active:
                viewport.cancel_context_pick()
                return
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
                finished=lambda: dialog.set_picking(False),
            )

        dialog.picking_changed.connect(toggle)
        dialog.coordinates.changed.connect(
            lambda: show_position_preview(viewport, dialog.coordinates.value())
        )

    def _connect_element_picking(self, dialog, part_id) -> None:
        viewport = self._viewport()
        if viewport is None:
            dialog.pick_button.setEnabled(False)
            return

        def preview(_value=None):
            self._preview_dialog_connectivity(part_id, dialog)

        dialog.connectivity_changed.connect(preview)

        def toggle(active):
            if not active:
                viewport.cancel_context_pick()
                return
            viewport.set_display_mode("mesh")
            policy = SelectionPolicy.create(
                {SelectableKind.MESH_NODE},
                multiple=True,
            )

            def selected(hit):
                if hit.mesh_id is None:
                    return
                dialog.apply_picked_node(
                    int(hit.mesh_id),
                    remove=(hit.selection_operation is SelectionOperation.REMOVE),
                )

            viewport.begin_selection_session(
                policy,
                selected,
                finished=lambda: dialog.set_picking(False),
            )

        dialog.picking_changed.connect(toggle)

    def _preview_dialog_connectivity(self, part_id, dialog) -> None:
        part = self._live_part(part_id, quiet=True)
        if part is None:
            return
        values = dialog.values()
        show_connectivity_preview(
            self._viewport(),
            part.mesh,
            values["node_ids"],
            values["element_type"],
        )

    def _node_details(self, part, node_id) -> dict:
        report = validate_node_move(part.mesh, node_id, part.mesh.node(node_id).coordinates)
        invalid = report.invalid_ids
        validation = (
            "No incident elements"
            if not report.elements
            else "Valid"
            if not invalid
            else "Invalid incident element(s): " + ", ".join(map(str, invalid))
        )
        return {
            "incident_elements": part.mesh.incident_element_ids(node_id),
            "regions": self._region_memberships(part, node_id, RegionProjection.NODES),
            "associations": self._association_labels(part, node_id, nodes=True),
            "validation": validation,
        }

    def _element_details(self, part, element) -> dict:
        validation = validate_element(element)
        flags = []
        if validation.inverted:
            flags.append("inverted")
        if validation.degenerate:
            flags.append("degenerate")
        if validation.collapsed:
            flags.append("collapsed")
        validation_text = "Valid" if not flags else "Invalid: " + ", ".join(flags)
        return {
            "regions": self._region_memberships(
                part,
                element.id,
                RegionProjection.ELEMENTS,
            ),
            "sections": self._section_memberships(part, element.id),
            "associations": self._association_labels(
                part,
                element.id,
                nodes=False,
            ),
            "validation": validation_text,
        }

    def _region_memberships(self, part, member_id, projection) -> tuple[str, ...]:
        project = self.ctx.store.project
        resolver = RegionResolver(project)
        requirement = RegionRequirement(
            projection=projection,
            allowed_dimensions=(0, 1, 2, 3) if projection is RegionProjection.NODES else (1, 2, 3),
            min_count=0,
        )
        result = []
        for region in part.regions:
            resolved = resolver.resolve(
                region.definition,
                requirement,
                allow_part_local=True,
            )
            members = resolved.nodes if projection is RegionProjection.NODES else resolved.elements
            if any(
                item.owner_id == part.id
                and (
                    item.node_id if projection is RegionProjection.NODES else item.element_id
                ) == int(member_id)
                for item in members
            ):
                result.append(region.name)
        return tuple(result)

    def _section_memberships(self, part, element_id) -> tuple[str, ...]:
        project = self.ctx.store.project
        resolver = RegionResolver(project)
        requirement = RegionRequirement(
            projection=RegionProjection.ELEMENTS,
            allowed_dimensions=(1, 2, 3),
            min_count=0,
        )
        labels = []
        for assignment in part.section_assignments:
            resolved = resolver.resolve(
                assignment.target,
                requirement,
                allow_part_local=True,
            )
            if not any(
                item.owner_id == part.id and item.element_id == int(element_id)
                for item in resolved.elements
            ):
                continue
            section = project.try_resolve(assignment.section_ref)
            if section is None:
                labels.append(assignment.name)
                continue
            material = project.try_resolve(getattr(section, "material_ref", None))
            labels.append(
                f"{section.name} / {material.name}" if material is not None else section.name
            )
        return tuple(labels)

    @staticmethod
    def _association_labels(part, member_id, *, nodes) -> tuple[str, ...]:
        stores = [part.mesh.associations.nodes] if nodes else [
            part.mesh.associations.elements,
            part.mesh.associations.facets,
        ]
        result = []
        for store in stores:
            for geometry, values in store.typed_items():
                if store.value_kind == "facets":
                    found = any(int(value[0]) == int(member_id) for value in values)
                else:
                    found = any(int(value) == int(member_id) for value in values)
                if found and str(geometry) not in result:
                    result.append(str(geometry))
        return tuple(result)

    def _part(self):
        part = self.ctx.active_part()
        if part is None:
            self.ctx.store.message.emit("Create or activate a Part first")
        return part

    def _live_part(self, part_id, *, quiet=False):
        part = self.ctx.store.project.try_resolve(part_id)
        if part is None and not quiet:
            self.ctx.store.message.emit("The edited Part no longer exists")
        return part

    def _selected_ids(self, kind: SelectableKind) -> tuple[int, ...]:
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

    def _execute(self, description, command, part_id) -> bool:
        try:
            self.ctx.store.execute(description, command)
        except (KeyError, RuntimeError, TypeError, ValueError) as exc:
            self.ctx.error("Mesh edit failed", exc)
            return False
        self.ctx.store.invalidate_scene(description)
        viewport = self._viewport()
        if viewport is not None:
            viewport.set_display_mode("mesh")
        part = self._live_part(part_id, quiet=True)
        invalid = (
            tuple(part.mesh.quality.invalid_element_ids)
            if part is not None
            else ()
        )
        if invalid:
            self.ctx.store.message.emit(
                f"{description}; mesh contains {len(invalid)} invalid element(s)"
            )
        return True

    @staticmethod
    def _command(commands):
        commands = tuple(commands)
        if not commands:
            raise ValueError("A mesh edit requires at least one command")
        return commands[0] if len(commands) == 1 else CompositeCommand(commands)

    def _track(self, dialog, *, clear_preview=False) -> None:
        self._dialogs.append(dialog)

        def finished(_code):
            if dialog in self._dialogs:
                self._dialogs.remove(dialog)
            viewport = self._viewport()
            if viewport is not None:
                viewport.cancel_context_pick()
            if clear_preview:
                clear_mesh_edit_preview(viewport)

        dialog.finished.connect(finished)
        show_modeless_dialog(dialog)

    def _close_existing_dialogs(self) -> None:
        for dialog in tuple(self._dialogs):
            dialog.close()
        self._dialogs.clear()
        viewport = self._viewport()
        if viewport is not None:
            viewport.cancel_context_pick()
        clear_mesh_edit_preview(viewport)

    def _viewport(self):
        return getattr(self.ctx.parent, "viewport", None)
