from __future__ import annotations

import numpy as np

from .cell_selection import pick_cell
from .element_selection_state import ElementSelectionState
from .picker_entities import actor_entity, actor_kind, selection_operation
from .point_selection_state import PointSelectionState
from .pyvista_geometry import set_actor_selected
from opencae.model.selection import SelectableKind, SelectionOperation, ViewportSelection


_POINT_PICK_TOLERANCE = 0.012
_EDGE_PICK_TOLERANCE = 0.018
_POINT_SNAP_PIXELS = 11.0
_EDGE_SNAP_PIXELS = 15.0
_POINT_EDGE_BIAS_PIXELS = 2.0
_DEPTH_EPSILON = 0.008


_POINT_KINDS = {
    SelectableKind.GEOMETRY_VERTEX,
    SelectableKind.REFERENCE_POINT,
    SelectableKind.DATUM_POINT,
}


class PyVistaPicker:
    def __init__(self, owner):
        self.owner = owner
        self.selected_actors = set()
        self.selected_cells = set()
        self.points = PointSelectionState(owner)
        self.elements = ElementSelectionState(owner)

    def enable(self):
        self.configure()

    def configure(self):
        try:
            self.owner.plotter.disable_picking()
        except Exception as exc:
            self.owner.message.emit(f"Could not reset viewport picker: {exc}")

        mode = self.owner.selection_mode
        # VTK pickers may snapshot their pick list when enabled. Configure the
        # exact actor set for the selected topology mode first.
        self.update_pickability()
        if (
            self.owner.stage == "RESULTS"
            or not self.owner.context_pick.active
            or mode == "none"
        ):
            return

        try:
            if mode == "point" and self.owner.display_mode == "mesh":
                # Mesh nodes are genuine mesh points, so the VTK point picker is
                # appropriate here. CAD/reference/datum points use the common
                # screen-space geometry path below instead.
                self.owner.plotter.enable_point_picking(
                    callback=self.points.picked,
                    tolerance=_POINT_PICK_TOLERANCE,
                    left_clicking=True,
                    show_message=False,
                    show_point=False,
                    picker="point",
                    pickable_window=False,
                    clear_on_no_selection=True,
                )
            elif mode == "element" or (
                mode == "auto"
                and self.owner.display_mode == "mesh"
                and not self.owner.context_pick.allowed
                & {SelectableKind.DATUM_VECTOR, SelectableKind.DATUM_PLANE}
            ):
                self.owner.plotter.enable_surface_point_picking(
                    callback=self.elements.picked,
                    tolerance=_EDGE_PICK_TOLERANCE,
                    left_clicking=True,
                    show_message=False,
                    show_point=False,
                    picker="cell",
                    pickable_window=False,
                )
            elif self.owner.display_mode == "geometry" and mode in {
                "point",
                "edge",
                "auto",
            }:
                # The cell picker supplies only cursor/depth information. The
                # selected CAD point/edge is chosen deterministically below by
                # measuring every allowed visible candidate in screen pixels.
                self.owner.plotter.enable_surface_point_picking(
                    callback=self.picked_geometry,
                    tolerance=_EDGE_PICK_TOLERANCE,
                    left_clicking=True,
                    show_message=False,
                    show_point=False,
                    picker="cell",
                    use_picker=True,
                    pickable_window=True,
                    clear_on_no_selection=False,
                )
            else:
                self.owner.plotter.enable_mesh_picking(
                    callback=self.picked_actor,
                    use_actor=True,
                    show=False,
                    show_message=False,
                    picker="hardware",
                    left_clicking=True,
                )
        except Exception as exc:
            self.owner.message.emit(f"Could not configure {mode} picking: {exc}")

    def clear(self, emit=True, render=True):
        for actor in tuple(self.selected_actors):
            set_actor_selected(actor, False, actor_kind(self.owner.scene, actor))
        self.selected_actors.clear()
        self.selected_cells.clear()
        self.points.clear()
        self.elements.clear()
        preview = getattr(self.owner.scene, "selection_preview_overlay", None)
        if preview is not None:
            preview.reapply_actor_styles()
        if emit:
            self.owner.selection_changed.emit(None)
        if render:
            self.owner.plotter.render()

    def reset(self):
        self.selected_actors.clear()
        self.selected_cells.clear()
        self.points.clear()
        self.elements.clear()

    def picked_geometry(self, _point, picker=None):
        mode = self.owner.selection_mode
        picked_actor = _picker_actor(picker)
        cursor = _selection_point(picker)
        picked_depth = _picked_depth(self.owner.plotter.renderer, picker)

        actor = None
        if mode == "point":
            if cursor is not None:
                actor, _distance = self._nearest_point_actor(
                    cursor,
                    _POINT_SNAP_PIXELS,
                    picked_depth,
                )
            elif self._actor_is_accepted(picked_actor):
                actor = picked_actor
        elif mode == "edge":
            actor, _distance = self._nearest_edge_actor(
                picker,
                _EDGE_SNAP_PIXELS,
                picked_depth,
            )
        elif mode == "auto":
            actor = self._preferred_auto_actor(
                picker,
                picked_actor,
                cursor=cursor,
                picked_depth=picked_depth,
            )

        if actor is not None:
            self.picked_actor(actor)

    def _preferred_auto_actor(
        self,
        picker,
        picked_actor,
        *,
        cursor=None,
        picked_depth=None,
    ):
        cursor = _selection_point(picker) if cursor is None else cursor
        if cursor is None:
            return picked_actor if self._actor_is_accepted(picked_actor) else None

        if picked_depth is None:
            picked_depth = _picked_depth(self.owner.plotter.renderer, picker)
        point_actor, point_distance = self._nearest_point_actor(
            cursor,
            _POINT_SNAP_PIXELS,
            picked_depth,
        )
        edge_actor, edge_distance = self._nearest_edge_actor(
            picker,
            _EDGE_SNAP_PIXELS,
            picked_depth,
        )

        if point_actor is not None and edge_actor is not None:
            # Standalone point markers are visually small. Give a point a tiny
            # bias when it is essentially as close as an edge, while still
            # letting an obviously nearer edge win.
            return (
                point_actor
                if point_distance <= edge_distance + _POINT_EDGE_BIAS_PIXELS
                else edge_actor
            )
        if point_actor is not None:
            return point_actor
        if edge_actor is not None:
            return edge_actor
        return picked_actor if self._actor_is_accepted(picked_actor) else None

    def _nearest_point_actor(self, cursor, maximum, picked_depth=None):
        scene = self.owner.scene
        candidates = []
        for actor in (
            *scene.vertex_actors,
            *scene.reference_actors,
            *scene.datum_actors,
        ):
            if not _actor_enabled(actor):
                continue
            hit = actor_entity(scene, actor)
            if (
                hit is None
                or hit.world_position is None
                or hit.kind not in _POINT_KINDS
                or not self.owner.context_pick.accepts(hit.kind)
            ):
                continue
            display = _world_to_display(
                self.owner.plotter.renderer,
                hit.world_position,
            )
            if display is None:
                continue
            if (
                picked_depth is not None
                and display[2] > picked_depth + _DEPTH_EPSILON
            ):
                continue
            distance = float(np.linalg.norm(display[:2] - cursor))
            if distance > maximum:
                continue
            # If two markers are effectively coincident, prefer an explicit
            # datum/reference marker over a generated CAD vertex.
            kind_priority = (
                1 if hit.kind == SelectableKind.GEOMETRY_VERTEX else 0
            )
            candidates.append((distance, kind_priority, display[2], actor))
        if not candidates:
            return None, float("inf")
        distance, _priority, _depth, actor = min(
            candidates,
            key=lambda item: (item[0], item[1], item[2]),
        )
        return actor, distance

    def _nearest_edge_actor(self, picker, maximum, picked_depth=None):
        cursor = _selection_point(picker)
        if cursor is None:
            return None, float("inf")
        if picked_depth is None:
            picked_depth = _picked_depth(self.owner.plotter.renderer, picker)

        candidates = []
        for actor in self.owner.scene.edge_actors:
            if not _actor_enabled(actor):
                continue
            hit = actor_entity(self.owner.scene, actor)
            if hit is None or not self.owner.context_pick.accepts(hit.kind):
                continue
            distance, depth = _edge_screen_distance(
                self.owner.plotter.renderer,
                actor,
                cursor,
                maximum,
            )
            if distance > maximum:
                continue
            if (
                picked_depth is not None
                and depth is not None
                and depth > picked_depth + _DEPTH_EPSILON
            ):
                continue
            candidates.append((distance, depth if depth is not None else 1.0, actor))
        if not candidates:
            return None, float("inf")
        distance, _depth, actor = min(
            candidates,
            key=lambda item: (item[0], item[1]),
        )
        return actor, distance

    def _actor_is_accepted(self, actor):
        if actor is None:
            return False
        hit = actor_entity(self.owner.scene, actor)
        return bool(hit and self.owner.context_pick.accepts(hit.kind))

    def picked_actor(self, actor):
        scene = self.owner.scene
        kind = actor_kind(scene, actor)
        valid = (
            actor in scene.face_actors
            or actor in scene.edge_actors
            or actor in scene.vertex_actors
            or actor in scene.reference_actors
            or actor in scene.datum_actors
        )
        if not valid:
            return
        if self.owner.selection_mode == "cell":
            pick_cell(self, actor)
            return
        allowed = self.owner.selection_mode in {"auto", kind} or (
            self.owner.selection_mode == "point"
            and kind in {"vertex", "rp", "datum_point"}
        )
        if not allowed:
            return
        operation = selection_operation()
        hit = actor_entity(scene, actor)
        if hit is None:
            return
        if self.owner.context_pick.active:
            # Dialog-owned region previews are the sole visual source of truth.
            self.emit_entities((), (hit.with_operation(operation),))
            return
        if operation == SelectionOperation.REPLACE:
            self.clear(False, False)
            self.selected_actors.add(actor)
            set_actor_selected(actor, True, kind)
        elif operation == SelectionOperation.REMOVE:
            self.selected_actors.discard(actor)
            set_actor_selected(actor, False, kind)
        else:
            self.selected_actors.add(actor)
            set_actor_selected(actor, True, kind)
        self.emit_entities(
            [
                item
                for item in (
                    actor_entity(scene, current)
                    for current in self.selected_actors
                )
                if item
            ],
            [hit.with_operation(operation)],
        )

    def emit_entities(self, entities, event_entities=None):
        if self.owner.handle_entities(event_entities or entities):
            self.clear(False, False)
        else:
            self.owner.selection_changed.emit(
                ViewportSelection.from_hits(entities) if entities else None
            )
        self.owner.plotter.render()

    def show_labels(self, values, render=True):
        from opencae.model.selection import RegionDefinition, selection_item_label

        project = self.owner.store.project
        definition = RegionDefinition.from_values(values)
        self.clear(False, False)
        wanted = {
            selection_item_label(project, item)
            for item in definition.items
        }
        actors = (
            *self.owner.scene.face_actors,
            *self.owner.scene.edge_actors,
            *self.owner.scene.vertex_actors,
            *self.owner.scene.reference_actors,
            *self.owner.scene.datum_actors,
        )
        for actor in actors:
            entity = actor_entity(self.owner.scene, actor)
            if entity and entity.label in wanted:
                self.selected_actors.add(actor)
                set_actor_selected(
                    actor,
                    True,
                    actor_kind(self.owner.scene, actor),
                )
        if render:
            self.owner.plotter.render()

    def update_pickability(self):
        mode = self.owner.selection_mode
        scene = self.owner.scene
        context = self.owner.context_pick
        active = (
            context.active
            and self.owner.stage != "RESULTS"
            and mode != "none"
        )
        if active:
            kinds = context.policy.accepted_kinds
            point_enabled = mode in {"auto", "point"} and bool(
                kinds & _POINT_KINDS
            )
            edge_enabled = (
                mode in {"auto", "edge"}
                and SelectableKind.GEOMETRY_EDGE in kinds
            )
            face_enabled = (
                mode in {"auto", "face"}
                and SelectableKind.GEOMETRY_FACE in kinds
            )
            cell_enabled = (
                mode in {"auto", "cell"}
                and SelectableKind.GEOMETRY_CELL in kinds
            )

            # In CAD point/edge modes faces remain pickable only so vtkCellPicker
            # can tell us the visible surface depth under the mouse. They are not
            # emitted unless the policy actually accepts a face.
            depth_surface = (
                self.owner.display_mode == "geometry"
                and mode in {"point", "edge", "auto"}
                and (point_enabled or edge_enabled)
            )
            for actor in scene.face_actors:
                actor.SetPickable(
                    face_enabled or cell_enabled or depth_surface
                )
            for actor in scene.edge_actors:
                actor.SetPickable(edge_enabled)
                actor.GetProperty().SetLineWidth(
                    5.2 if mode == "edge" else (4.3 if edge_enabled else 3.6)
                )
            for actor in scene.vertex_actors:
                enabled = (
                    mode in {"auto", "point"}
                    and SelectableKind.GEOMETRY_VERTEX in kinds
                )
                actor.SetPickable(enabled)
                actor.SetVisibility(
                    self.owner.display_mode == "geometry" and enabled
                )
                actor.GetProperty().SetPointSize(
                    13.0 if mode == "point" and enabled else (10.0 if enabled else 8.0)
                )
            for actor in scene.reference_actors:
                actor.SetPickable(
                    mode in {"auto", "point"}
                    and SelectableKind.REFERENCE_POINT in kinds
                )
            for actor, hit in scene.datum_actors.items():
                kind = getattr(hit, "kind", None)
                is_point = kind == SelectableKind.DATUM_POINT
                actor.SetPickable(
                    kind in kinds
                    and (
                        (is_point and mode in {"auto", "point"})
                        or (not is_point and mode == "auto")
                    )
                )
            mesh_pickable = self.owner.display_mode == "mesh" and (
                (
                    mode in {"auto", "point"}
                    and SelectableKind.MESH_NODE in kinds
                )
                or (
                    mode in {"auto", "element"}
                    and bool(
                        kinds
                        & {
                            SelectableKind.MESH_ELEMENT,
                            SelectableKind.MESH_FACET,
                        }
                    )
                )
            )
            if scene.mesh_actor is not None:
                scene.mesh_actor.SetPickable(mesh_pickable)
            for actor in scene.mesh_actors:
                actor.SetPickable(mesh_pickable)
            return

        # No free-form viewport selection exists outside a dialog-owned session.
        for actor in scene.face_actors:
            actor.SetPickable(False)
        for actor in scene.edge_actors:
            actor.SetPickable(False)
            actor.GetProperty().SetLineWidth(3.6)
        for actor in scene.vertex_actors:
            actor.SetPickable(False)
            actor.SetVisibility(False)
            actor.GetProperty().SetPointSize(8.0)
        for actor in scene.reference_actors:
            actor.SetPickable(False)
        for actor in scene.datum_actors:
            actor.SetPickable(False)
        if scene.mesh_actor is not None:
            scene.mesh_actor.SetPickable(False)
        for actor in scene.mesh_actors:
            actor.SetPickable(False)


def _picker_actor(picker):
    if picker is None:
        return None
    try:
        return picker.GetActor()
    except (AttributeError, RuntimeError):
        return None


def _selection_point(picker):
    if picker is None:
        return None
    try:
        point = np.asarray(
            picker.GetSelectionPoint(),
            dtype=float,
        ).reshape(-1)
        return (
            point[:2]
            if len(point) >= 2 and np.all(np.isfinite(point[:2]))
            else None
        )
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return None


def _picked_depth(renderer, picker):
    if _picker_actor(picker) is None:
        return None
    try:
        display = _world_to_display(renderer, picker.GetPickPosition())
        return None if display is None else float(display[2])
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return None


def _world_to_display(renderer, point):
    try:
        values = np.asarray(point, dtype=float).reshape(-1)
        if len(values) < 3 or not np.all(np.isfinite(values[:3])):
            return None
        renderer.SetWorldPoint(
            float(values[0]),
            float(values[1]),
            float(values[2]),
            1.0,
        )
        renderer.WorldToDisplay()
        display = np.asarray(renderer.GetDisplayPoint(), dtype=float)
        return (
            display
            if len(display) >= 3 and np.all(np.isfinite(display[:3]))
            else None
        )
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return None


def _edge_screen_distance(renderer, actor, cursor, maximum):
    try:
        data = actor.GetMapper().GetInput()
        count = int(data.GetNumberOfPoints())
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return float("inf"), None
    if count < 2 or not _cursor_near_bounds(
        renderer,
        actor,
        cursor,
        maximum,
    ):
        return float("inf"), None

    display = []
    for index in range(count):
        point = _world_to_display(renderer, data.GetPoint(index))
        if point is None:
            return float("inf"), None
        display.append(point)
    display = np.asarray(display, dtype=float)

    segments = []
    try:
        for cell_index in range(int(data.GetNumberOfCells())):
            cell = data.GetCell(cell_index)
            ids = [
                int(cell.GetPointId(i))
                for i in range(int(cell.GetNumberOfPoints()))
            ]
            segments.extend(zip(ids[:-1], ids[1:]))
    except (AttributeError, TypeError, ValueError, RuntimeError):
        segments = []
    if not segments:
        segments = list(zip(range(count - 1), range(1, count)))

    indices = np.asarray(segments, dtype=int)
    start = display[indices[:, 0]]
    stop = display[indices[:, 1]]
    delta = stop[:, :2] - start[:, :2]
    length_sq = np.einsum("ij,ij->i", delta, delta)
    relative = cursor - start[:, :2]
    parameters = np.zeros(len(indices), dtype=float)
    valid = length_sq > 1.0e-12
    parameters[valid] = (
        np.einsum("ij,ij->i", relative[valid], delta[valid])
        / length_sq[valid]
    )
    parameters = np.clip(parameters, 0.0, 1.0)
    closest = start[:, :2] + parameters[:, None] * delta
    distances = np.linalg.norm(closest - cursor, axis=1)
    best = int(np.argmin(distances))
    depth = float(
        start[best, 2]
        + parameters[best] * (stop[best, 2] - start[best, 2])
    )
    return float(distances[best]), depth


def _cursor_near_bounds(renderer, actor, cursor, margin):
    try:
        xmin, xmax, ymin, ymax, zmin, zmax = map(float, actor.GetBounds())
        corners = [
            (x, y, z)
            for x in (xmin, xmax)
            for y in (ymin, ymax)
            for z in (zmin, zmax)
        ]
        projected = [
            value
            for point in corners
            if (value := _world_to_display(renderer, point)) is not None
        ]
        if not projected:
            return True
        values = np.asarray(projected)
        return bool(
            values[:, 0].min() - margin
            <= cursor[0]
            <= values[:, 0].max() + margin
            and values[:, 1].min() - margin
            <= cursor[1]
            <= values[:, 1].max() + margin
        )
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return True


def _actor_enabled(actor):
    visibility = getattr(actor, "GetVisibility", lambda: True)()
    pickable = getattr(actor, "GetPickable", lambda: True)()
    return bool(visibility and pickable)
