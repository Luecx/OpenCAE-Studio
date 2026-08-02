from .assembly_context import ActorReference
from .picker_entities import additive_selection
from .pyvista_geometry import set_actor_selected


def pick_cell(picker, actor):
    scene = picker.owner.scene
    reference = scene.face_actors.get(actor)
    if reference is None: return
    if not isinstance(reference, ActorReference):
        reference = ActorReference(None, 2, int(reference))
    snapshot = scene.snapshot_for(reference.instance_name)
    cells = snapshot.surface_to_cells.get(reference.tag, []) if snapshot else []
    if not cells: return
    targets = {(reference.instance_name, int(cell)) for cell in cells}
    if not additive_selection(): picker.clear(False, False)
    if targets.issubset(picker.selected_cells): picker.selected_cells.difference_update(targets)
    else: picker.selected_cells.update(targets)
    picker.selected_actors.clear()
    for item, face_ref in scene.face_actors.items():
        face_ref = face_ref if isinstance(face_ref, ActorReference) else ActorReference(None, 2, int(face_ref))
        face_snapshot = scene.snapshot_for(face_ref.instance_name)
        active = any(
            instance == face_ref.instance_name and cell in face_snapshot.surface_to_cells.get(face_ref.tag, [])
            for instance, cell in picker.selected_cells
        ) if face_snapshot else False
        set_actor_selected(item, active, "face")
        if active: picker.selected_actors.add(item)
    entities = []
    for instance, tag in sorted(picker.selected_cells, key=lambda value: (value[0] or "", value[1])):
        label = f"Cell-{tag}"; label = f"{instance}.{label}" if instance else label
        owner = scene.instance_for(instance) if instance else None
        entities.append({"name": label, "kind": "cell", "dimension": 3, "tag": tag, "instance": instance, "instance_id": getattr(owner, "id", None)})
    picker.emit_entities(entities)
