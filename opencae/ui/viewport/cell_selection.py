from opencae.model.selection import SelectableKind, SelectionOperation, ViewportHit
from .assembly_context import ActorReference
from .picker_entities import selection_operation
from .pyvista_geometry import set_actor_selected


def pick_cell(picker, actor):
    scene = picker.owner.scene
    reference = scene.face_actors.get(actor)
    if reference is None:
        return
    if not isinstance(reference, ActorReference):
        reference = ActorReference(None, 2, int(reference))
    snapshot = scene.snapshot_for(reference.instance_id)
    cells = snapshot.surface_to_cells.get(reference.tag, []) if snapshot else []
    if not cells:
        return
    occurrence = reference.instance_id
    targets = {(occurrence, int(cell)) for cell in cells}
    operation = selection_operation()
    if operation == SelectionOperation.REPLACE:
        picker.clear(False, False)
        picker.selected_cells.update(targets)
    elif operation == SelectionOperation.REMOVE:
        picker.selected_cells.difference_update(targets)
    else:
        picker.selected_cells.update(targets)
    picker.selected_actors.clear()
    for item, face_ref in scene.face_actors.items():
        face_ref = face_ref if isinstance(face_ref, ActorReference) else ActorReference(None, 2, int(face_ref))
        face_snapshot = scene.snapshot_for(face_ref.instance_id)
        active = any(
            instance == face_ref.instance_id and cell in face_snapshot.surface_to_cells.get(face_ref.tag, [])
            for instance, cell in picker.selected_cells
        ) if face_snapshot else False
        set_actor_selected(item, active, "face")
        if active:
            picker.selected_actors.add(item)
    hits = [_cell_hit(scene, instance_key, tag) for instance_key, tag in sorted(
        picker.selected_cells, key=lambda value: (value[0] or "", value[1])
    )]
    changed = [_cell_hit(scene, instance_key, tag) for instance_key, tag in sorted(
        targets, key=lambda value: (value[0] or "", value[1])
    )]
    if operation == SelectionOperation.REPLACE:
        event_hits = [
            hit.with_operation(SelectionOperation.REPLACE if index == 0 else SelectionOperation.ADD)
            for index, hit in enumerate(changed)
        ]
    else:
        event_hits = [hit.with_operation(operation) for hit in changed]
    picker.emit_entities(hits, event_hits)


def _cell_hit(scene, instance_id, tag):
    instance = scene.instance_for(instance_id) if instance_id else None
    label = f"Cell-{tag}"
    if instance:
        label = f"{instance.name}.{label}"
    return ViewportHit(
        kind=SelectableKind.GEOMETRY_CELL,
        instance_id=getattr(instance, "id", None),
        topology_tag=int(tag),
        dimension=3,
        label=label,
    )
