"""Regression coverage for repicking the active target in Edit Node."""

from __future__ import annotations

from types import SimpleNamespace

from opencae.controllers.part.mesh_editing_interactive import InteractivePartMeshEditing
from opencae.model.entities.fem import MeshEntityOrigin, Node
from opencae.ui.other.dialogs.mesh_node import MeshNodeDialog


def _dispose(application, widget):
    widget.close()
    widget.deleteLater()
    application.processEvents()


def test_edit_node_dialog_can_start_without_a_preselected_target(qapplication):
    dialog = MeshNodeDialog(editing=True)
    try:
        assert dialog.values()["node_id"] is None
        assert dialog.target_pick_button is not None
        assert not dialog.coordinates.isEnabled()
        assert not dialog.position_pick_button.isEnabled()

        node = Node(7, (1.0, 2.0, 3.0), MeshEntityOrigin.AUTHORED)
        dialog.set_node(node, details={"incident_elements": (4, 5)})

        assert dialog.values()["node_id"] == 7
        assert dialog.values()["coordinates"] == (1.0, 2.0, 3.0)
        assert dialog.coordinates.isEnabled()
        assert dialog.position_pick_button.isEnabled()
    finally:
        _dispose(qapplication, dialog)


def test_edit_node_dialog_can_switch_from_one_node_to_another(qapplication):
    first = Node(3, (1.0, 0.0, 0.0), MeshEntityOrigin.AUTHORED)
    second = Node(9, (0.0, 4.0, 2.0), MeshEntityOrigin.AUTHORED)
    dialog = MeshNodeDialog(first, editing=True)
    try:
        dialog.set_coordinates((99.0, 99.0, 99.0))
        dialog.set_node(second, details={"validation": "Valid"})

        assert dialog.values()["node_id"] == 9
        assert dialog.values()["coordinates"] == second.coordinates
        assert dialog.node is second
    finally:
        _dispose(qapplication, dialog)


def test_edit_commit_uses_current_dialog_target_not_initial_selection():
    first = Node(1, (0.0, 0.0, 0.0), MeshEntityOrigin.AUTHORED)
    second = Node(2, (1.0, 0.0, 0.0), MeshEntityOrigin.AUTHORED)
    nodes = {1: first, 2: second}
    part = SimpleNamespace(
        id="part-1",
        mesh=SimpleNamespace(node=lambda node_id: nodes[int(node_id)]),
    )
    project = SimpleNamespace(try_resolve=lambda _value: part)
    store = SimpleNamespace(project=project)
    context = SimpleNamespace(
        store=store,
        parent=None,
        error=lambda *_args: None,
    )
    editor = InteractivePartMeshEditing(context)
    captured = []
    editor._execute = lambda description, command, part_id: captured.append(
        (description, command, part_id)
    ) or True
    dialog = SimpleNamespace(
        values=lambda: {"node_id": 2, "coordinates": (4.0, 5.0, 6.0)}
    )

    editor._commit_edited_node(part.id, dialog)

    assert len(captured) == 1
    description, command, part_id = captured[0]
    assert description == "Moved node 2"
    assert part_id == part.id
    assert command.before.id == 2
    assert command.after.id == 2
    assert command.after.coordinates == (4.0, 5.0, 6.0)
