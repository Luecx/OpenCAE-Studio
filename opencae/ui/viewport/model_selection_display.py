from PyQt6.QtCore import QTimer


def show_model_selection(viewport, entity):
    from opencae.model.entities.fields import FieldDefinition
    from opencae.model.regions import Region
    if isinstance(entity, FieldDefinition):
        viewport._field_id = entity.id
        if viewport.display_mode != "mesh":
            viewport.display_mode = "mesh"; viewport.request_refresh()
        elif viewport.scene.mesh_grid is not None:
            viewport.scene.show_field(entity)
        return
    if isinstance(entity, Region):
        viewport._pending_members = list(entity.members)
        target = "mesh" if _contains_mesh_members(entity.members) else "geometry"
        if viewport.display_mode != target:
            viewport.display_mode = target; viewport.toolbar.set_display(target); viewport.request_refresh()
        else:
            QTimer.singleShot(0, viewport._show_pending_members)
        return
    if viewport._field_id is not None and not isinstance(entity, dict):
        viewport._field_id = None; viewport.request_refresh()
    elif not isinstance(entity, dict):
        viewport.picker.clear(False); viewport.scene.region_overlay.clear(viewport.plotter); viewport.plotter.render()


def show_pending_members(viewport):
    if viewport._pending_members is None: return
    members = viewport._pending_members; viewport._pending_members = None
    viewport.picker.show_labels(members, render=False)
    viewport.scene.region_overlay.show(viewport.plotter, viewport.scene, members)
    viewport.plotter.render()


def highlight_members(viewport, members):
    viewport._pending_members = list(members or ())
    QTimer.singleShot(0, viewport._show_pending_members)


def _contains_mesh_members(members):
    return any(str(value).split(".")[-1].startswith(("Node-", "Element-")) for value in members)
