from __future__ import annotations

from dataclasses import replace
import logging
import re

import numpy as np
import pyvista as pv

from opencae.model.selection import (
    GeometryOperand,
    MeshElementOperand,
    MeshFacetOperand,
    MeshNodeOperand,
    NamedRegionOperand,
    ReferencePointOperand,
    RegionDefinition,
    RegionSelectionItem,
    WholeModelOperand,
    element_side_indices,
    selection_item_label,
)
from .assembly_context import ActorReference
from .instance_transform import transform_points
from .safe_operations import remove_actor
from .vtk_cell_data import cell_array

LOGGER = logging.getLogger(__name__)
_EXPECTED_PREVIEW_ERRORS = (AttributeError, KeyError, RuntimeError, TypeError, ValueError)


class SelectionPreviewOverlay:
    """Draw raw region operands in independent, persistent dialog channels.

    This overlay never calls ``RegionResolver``.  It shows exactly what the
    user selected: CAD sub-shapes, mesh entities, reference points, and the raw
    contents of named regions.  Semantic projection is deferred to deck generation.
    """

    def __init__(self):
        self._channels: dict[str, list[str]] = {}
        self._actor_overrides: dict[str, list[tuple[object, str, dict]]] = {}
        self._actor_base: dict[object, dict] = {}

    def clear(self, plotter):
        for channel in tuple(set(self._channels) | set(self._actor_overrides)):
            self.clear_channel(plotter, channel)

    def clear_channel(self, plotter, channel: str):
        channel = str(channel)
        for name in self._channels.pop(channel, ()):
            remove_actor(plotter, name)
        self._actor_overrides.pop(channel, None)
        self._apply_actor_styles()

    def reapply_actor_styles(self):
        """Restore persistent preview colors after the normal picker resets actors."""
        self._apply_actor_styles()

    def show_channel(
        self,
        plotter,
        scene,
        channel: str,
        definition,
        *,
        color="#ffd166",
        opacity=0.62,
        point_size=18,
        show_point_labels=False,
    ):
        channel = str(channel)
        self.clear_channel(plotter, channel)
        definition = _expanded(scene.owner.store.project, RegionDefinition.from_values(definition))
        if definition.empty:
            return
        names: list[str] = []
        actor_overrides: list[tuple[object, str, dict]] = []
        safe_channel = re.sub(r"[^A-Za-z0-9_.-]+", "-", channel)
        style = dict(
            color=color,
            opacity=float(opacity),
            point_size=float(point_size),
            show_point_labels=bool(show_point_labels),
        )
        for index, item in enumerate(definition.items):
            prefix = f"selection-preview-{safe_channel}-{index}"
            try:
                if isinstance(item.operand, GeometryOperand):
                    created, overrides = self._geometry(
                        plotter, scene, item.operand, item, prefix, **style
                    )
                    actor_overrides.extend(overrides)
                else:
                    created = self._draw_item(
                        plotter, scene, item, prefix, **style
                    )
            except _EXPECTED_PREVIEW_ERRORS as exc:
                LOGGER.warning("Could not preview selection item %s: %s", item.key, exc)
                created = []
            except Exception:
                LOGGER.exception("Unexpected failure while previewing selection item %s", item.key)
                created = []
            names.extend(created)
        self._channels[channel] = names
        self._actor_overrides[channel] = actor_overrides
        self._apply_actor_styles()

    def _draw_item(self, plotter, scene, item, prefix, **style):
        operand = item.operand
        if isinstance(operand, MeshNodeOperand):
            return self._mesh_node(plotter, scene, operand, item, prefix, **style)
        if isinstance(operand, MeshElementOperand):
            return self._mesh_element(plotter, scene, operand, prefix, **style)
        if isinstance(operand, MeshFacetOperand):
            return self._mesh_facet(plotter, scene, operand, prefix, **style)
        if isinstance(operand, ReferencePointOperand):
            return self._reference_point(plotter, scene, operand, item, prefix, **style)
        if isinstance(operand, WholeModelOperand):
            return self._whole_model(plotter, scene, operand, prefix, **style)
        return []

    def _geometry(self, plotter, scene, operand, item, prefix, **style):
        """Highlight the existing CAD actor instead of drawing a coplanar copy.

        Recoloring the actual rendered actor is the same robust mechanism used
        by normal viewport selection, so the highlight cannot disappear through
        z-fighting or depend on the camera angle.
        """
        actors = self._geometry_actors(scene, operand)
        kind = {0: "vertex", 1: "edge"}.get(int(operand.dimension), "face")
        overrides = []
        names = []
        for index, actor in enumerate(actors):
            self._remember_actor(actor)
            overrides.append((actor, kind, dict(style)))
            if int(operand.dimension) == 0 and style["show_point_labels"]:
                source = actor.GetMapper().GetInput()
                dataset = pv.wrap(source) if source is not None else None
                point = item.picked_position
                if point is None and dataset is not None and getattr(dataset, "n_points", 0):
                    point = tuple(np.asarray(dataset.points[0], dtype=float))
                if point is not None:
                    label_name = f"{prefix}-geometry-{index}-label"
                    plotter.add_point_labels(
                        np.asarray([point], dtype=float),
                        [selection_item_label(scene.owner.store.project, item)],
                        name=label_name, show_points=False, point_size=0, font_size=10,
                        text_color="#f7f9fb", shape_color="#20262d",
                        shape_opacity=.86, always_visible=True, render=False,
                    )
                    names.append(label_name)
        return names, overrides

    def _remember_actor(self, actor):
        if actor in self._actor_base:
            return
        prop = actor.GetProperty()
        self._actor_base[actor] = {
            "color": tuple(prop.GetColor()),
            "opacity": float(prop.GetOpacity()),
            "line_width": float(prop.GetLineWidth()),
            "point_size": float(prop.GetPointSize()),
            "edge_visibility": int(prop.GetEdgeVisibility()),
            "edge_color": tuple(prop.GetEdgeColor()),
            "lighting": int(prop.GetLighting()),
        }

    def _apply_actor_styles(self):
        active = {}
        for entries in self._actor_overrides.values():
            for actor, kind, style in entries:
                active[actor] = (kind, style)

        for actor, state in tuple(self._actor_base.items()):
            try:
                _restore_actor(actor, state)
            except (AttributeError, RuntimeError):
                self._actor_base.pop(actor, None)
                continue
            if actor not in active:
                self._actor_base.pop(actor, None)

        for actor, (kind, style) in active.items():
            try:
                self._remember_actor(actor)
                _style_actor(actor, kind, style, self._actor_base[actor])
            except (AttributeError, RuntimeError, TypeError, ValueError):
                LOGGER.warning("Could not apply persistent selection style to actor")

    def _geometry_actors(self, scene, operand):
        instance_id = operand.instance_ref.entity_id if operand.instance_ref else None
        if operand.dimension in (0, 1, 2):
            collection = {0: scene.vertex_actors, 1: scene.edge_actors, 2: scene.face_actors}[operand.dimension]
            return [
                actor for actor, reference in collection.items()
                if _matches_reference(reference, instance_id, operand.dimension, operand.tag)
            ]
        result = []
        snapshot = scene.snapshot_for(instance_id)
        if snapshot is None:
            return result
        for actor, reference in scene.face_actors.items():
            if not _matches_instance(reference, instance_id):
                continue
            tag = reference.tag if isinstance(reference, ActorReference) else int(reference)
            if int(operand.tag) in {int(value) for value in snapshot.surface_to_cells.get(tag, ())}:
                result.append(actor)
        return result

    def _mesh_node(self, plotter, scene, operand, item, prefix, **style):
        grid = _grid(scene, operand.instance_ref)
        if grid is None:
            return []
        try:
            ids = np.asarray(grid.point_data.get("node_id", ()))
        except (AttributeError, RuntimeError, RecursionError):
            return []
        indices = np.where(ids == int(operand.node_id))[0]
        if not len(indices):
            return []
        point = np.asarray([grid.points[int(indices[0])]])
        name = f"{prefix}-node"
        plotter.add_points(
            point,
            color=style["color"],
            point_size=style["point_size"],
            render_points_as_spheres=True,
            lighting=False,
            pickable=False,
            name=name,
            render=False,
        )
        names = [name]
        if style["show_point_labels"]:
            label_name = f"{prefix}-label"
            plotter.add_point_labels(
                point,
                [selection_item_label(scene.owner.store.project, item)],
                name=label_name,
                show_points=False,
                point_size=0,
                font_size=10,
                text_color="#f7f9fb",
                shape_color="#20262d",
                shape_opacity=.86,
                always_visible=True,
                render=False,
            )
            names.append(label_name)
        return names

    def _mesh_element(self, plotter, scene, operand, prefix, **style):
        grid = _grid(scene, operand.instance_ref)
        if grid is None:
            return []
        ids = cell_array(grid, "element_id")
        indices = np.where(ids == int(operand.element_id))[0]
        if not len(indices):
            return []
        name = f"{prefix}-element"
        actor = plotter.add_mesh(
            grid.extract_cells([int(indices[0])]),
            color=style["color"],
            opacity=max(style["opacity"], .82),
            show_edges=True,
            edge_color=style["color"],
            line_width=3.0,
            lighting=False,
            pickable=False,
            name=name,
            render=False,
        )
        _promote_overlay(actor)
        return [name]

    def _mesh_facet(self, plotter, scene, operand, prefix, **style):
        grid = _grid(scene, operand.instance_ref)
        if grid is None:
            return []
        ids = cell_array(grid, "element_id")
        indices = np.where(ids == int(operand.element_id))[0]
        if not len(indices):
            return []
        cell = grid.get_cell(int(indices[0]))
        side = str(operand.local_face or "")
        if side == "SPOS" or cell.dimension == 2:
            points = np.asarray(cell.points)
        else:
            topology = _element_topology(scene, operand.instance_ref, operand.element_id)
            face_indices = next((values for name, values in element_side_indices(topology) if name == side), ())
            points = np.asarray(cell.points)[[index for index in face_indices if index < len(cell.points)]]
        if len(points) < 3:
            return self._mesh_element(plotter, scene, MeshElementOperand(
                operand.owner_ref, operand.element_id, operand.instance_ref, operand.mesh_revision
            ), prefix, **style)
        mesh = pv.PolyData(points)
        mesh.faces = np.asarray([len(points), *range(len(points))])
        name = f"{prefix}-facet"
        actor = plotter.add_mesh(
            mesh,
            color=style["color"],
            opacity=max(style["opacity"], .86),
            show_edges=True,
            edge_color=style["color"],
            line_width=4.0,
            lighting=False,
            pickable=False,
            name=name,
            render=False,
        )
        _promote_overlay(actor)
        return [name]

    def _reference_point(self, plotter, scene, operand, item, prefix, **style):
        project = scene.owner.store.project
        point = project.try_resolve(operand.reference_point_ref)
        if point is None:
            return []
        position = np.asarray(point.position, dtype=float)
        instance = project.try_resolve(operand.instance_ref) if operand.instance_ref else None
        if instance is not None:
            position = transform_points([position], instance)[0]
        values = np.asarray([position])
        name = f"{prefix}-rp"
        plotter.add_points(
            values,
            color=style["color"],
            point_size=style["point_size"],
            render_points_as_spheres=True,
            lighting=False,
            pickable=False,
            name=name,
            render=False,
        )
        names = [name]
        if style["show_point_labels"]:
            label_name = f"{prefix}-label"
            plotter.add_point_labels(
                values,
                [selection_item_label(project, item)],
                name=label_name,
                show_points=False,
                point_size=0,
                font_size=10,
                text_color="#f7f9fb",
                shape_color="#20262d",
                shape_opacity=.86,
                always_visible=True,
                render=False,
            )
            names.append(label_name)
        return names

    def _whole_model(self, plotter, scene, operand, prefix, **style):
        grid = _grid(scene, operand.instance_ref)
        if grid is None:
            return []
        name = f"{prefix}-whole"
        actor = plotter.add_mesh(
            grid,
            color=style["color"],
            opacity=max(min(style["opacity"], .48), .32),
            show_edges=True,
            edge_color=style["color"],
            line_width=2.0,
            lighting=False,
            pickable=False,
            name=name,
            render=False,
        )
        _promote_overlay(actor)
        return [name]


def _restore_actor(actor, state):
    prop = actor.GetProperty()
    prop.SetColor(state["color"])
    prop.SetOpacity(state["opacity"])
    prop.SetLineWidth(state["line_width"])
    prop.SetPointSize(state["point_size"])
    prop.SetEdgeVisibility(state["edge_visibility"])
    prop.SetEdgeColor(state["edge_color"])
    prop.SetLighting(state["lighting"])


def _style_actor(actor, kind, style, base):
    prop = actor.GetProperty()
    rgb = pv.Color(style["color"]).float_rgb
    prop.SetColor(rgb)
    # Keep rendered CAD opaque like the normal blue viewport selection.  This
    # avoids the camera-angle-dependent disappearance caused by a translucent,
    # coplanar overlay mesh.
    prop.SetOpacity(max(float(base["opacity"]), .96))
    if kind == "face":
        prop.SetEdgeVisibility(1)
        prop.SetEdgeColor(rgb)
        prop.SetLineWidth(max(float(base["line_width"]), 2.0))
    elif kind == "edge":
        prop.SetLineWidth(max(float(base["line_width"]), 5.0))
    elif kind == "vertex":
        prop.SetPointSize(max(float(base["point_size"]), float(style["point_size"])))


def _promote_overlay(actor):
    """Bias extracted mesh previews toward the camera to suppress z-fighting."""
    try:
        mapper = actor.GetMapper()
        enable = getattr(mapper, "SetResolveCoincidentTopologyToPolygonOffset", None)
        if enable is not None:
            enable()
        polygon = getattr(mapper, "SetRelativeCoincidentTopologyPolygonOffsetParameters", None)
        if polygon is not None:
            polygon(-2.0, -2.0)
        line = getattr(mapper, "SetRelativeCoincidentTopologyLineOffsetParameters", None)
        if line is not None:
            line(-3.0, -3.0)
    except (AttributeError, RuntimeError, TypeError):
        pass


def _expanded(project, definition, inherited_instance=None, stack=None):
    stack = set(stack or ())
    result = []
    for item in RegionDefinition.from_values(definition).items:
        operand = item.operand
        if isinstance(operand, NamedRegionOperand):
            region = project.try_resolve(operand.region_ref)
            if region is None or region.id in stack:
                continue
            instance_ref = operand.instance_ref or inherited_instance
            result.extend(_expanded(project, region.definition, instance_ref, {*stack, region.id}).items)
            continue
        if inherited_instance and hasattr(operand, "instance_ref") and operand.instance_ref is None:
            operand = replace(operand, instance_ref=inherited_instance)
            item = RegionSelectionItem(operand, item.picked_position, item.display_label)
        result.append(item)
    return RegionDefinition(tuple(result))


def _grid(scene, instance_ref):
    instance_id = instance_ref.entity_id if instance_ref else None
    return scene.mesh_grids.get(instance_id) if instance_id else scene.mesh_grid


def _matches_reference(reference, instance_id, dimension, tag):
    if isinstance(reference, ActorReference):
        return reference.instance_id == instance_id and reference.dimension == int(dimension) and reference.tag == int(tag)
    return instance_id is None and int(reference) == int(tag)


def _matches_instance(reference, instance_id):
    return (reference.instance_id if isinstance(reference, ActorReference) else None) == instance_id


def _element_topology(scene, instance_ref, element_id):
    project = scene.owner.store.project
    instance = project.try_resolve(instance_ref) if instance_ref else None
    part = project.try_resolve(instance.part_ref) if instance else scene.owner.store.active_part()
    if part is None:
        return ""
    for block in part.mesh.element_blocks:
        if int(element_id) in {int(value) for value in block.ids}:
            return block.definition.topology
    return ""
