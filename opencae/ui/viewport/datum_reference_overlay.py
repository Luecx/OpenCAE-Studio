from __future__ import annotations

import re

import numpy as np
import pyvista as pv

from .safe_operations import remove_actor


_HIGHLIGHT = "#ffd166"
_LABEL_TEXT = "#fff8df"
_LABEL_BACKGROUND = "#3a321f"


class DatumReferenceOverlay:
    """Keep every reference used by an open datum dialog visible.

    Datum construction is sequential: for example Point 1 is chosen before
    Point 2, or an edge is chosen before a parameter is entered.  Normal picker
    state ends after each single click, so it cannot be the persistent visual
    source of truth.  This overlay remembers the dialog references and styles
    their existing actors until the dialog changes method or closes.
    """

    def __init__(self):
        self._actors: list[tuple[object, str]] = []
        self._base: dict[object, dict] = {}
        self._names: list[str] = []

    def clear(self, plotter):
        for name in self._names:
            remove_actor(plotter, name)
        self._names.clear()
        for actor, state in tuple(self._base.items()):
            try:
                _restore(actor, state)
            except (AttributeError, RuntimeError, TypeError):
                pass
        self._actors.clear()
        self._base.clear()

    def show(self, plotter, scene, references):
        self.clear(plotter)
        for index, reference in enumerate(tuple(references or ())):
            if not reference:
                continue
            reference = dict(reference)
            actor, actor_kind = _actor_for(scene, reference)
            if actor is not None:
                self._remember(actor)
                self._actors.append((actor, actor_kind))
                _style(actor, actor_kind)
            else:
                self._draw_fallback(plotter, reference, index)
            self._draw_label(plotter, reference, index)

    def reapply(self):
        for actor, actor_kind in tuple(self._actors):
            try:
                _style(actor, actor_kind)
            except (AttributeError, RuntimeError, TypeError, ValueError):
                continue

    def _remember(self, actor):
        if actor in self._base:
            return
        prop = actor.GetProperty()
        mapper = actor.GetMapper()
        self._base[actor] = {
            "visibility": int(actor.GetVisibility()),
            "pickable": int(actor.GetPickable()),
            "color": tuple(prop.GetColor()),
            "opacity": float(prop.GetOpacity()),
            "line_width": float(prop.GetLineWidth()),
            "point_size": float(prop.GetPointSize()),
            "edge_visibility": int(prop.GetEdgeVisibility()),
            "edge_color": tuple(prop.GetEdgeColor()),
            "lighting": int(prop.GetLighting()),
            "scalar_visibility": int(mapper.GetScalarVisibility()),
        }

    def _draw_fallback(self, plotter, reference, index):
        kind = str(reference.get("kind", ""))
        safe_kind = re.sub(r"[^A-Za-z0-9_.-]+", "-", kind or "reference")
        name = f"datum-reference-preview-{index}-{safe_kind}"
        if kind in {"vertex", "reference_point", "datum_point"}:
            point = _reference_point(reference)
            if point is None:
                return
            plotter.add_points(
                np.asarray([point]),
                color=_HIGHLIGHT,
                point_size=19,
                render_points_as_spheres=True,
                lighting=False,
                pickable=False,
                name=name,
                render=False,
            )
            self._names.append(name)
            return
        if kind == "edge":
            points = np.asarray(reference.get("points", ()), dtype=float)
            if points.ndim != 2 or len(points) < 2:
                return
            mesh = pv.PolyData(points)
            mesh.lines = np.asarray([len(points), *range(len(points))], dtype=np.int64)
            plotter.add_mesh(
                mesh,
                color=_HIGHLIGHT,
                line_width=7.0,
                render_lines_as_tubes=True,
                lighting=False,
                pickable=False,
                name=name,
                render=False,
            )
            self._names.append(name)

    def _draw_label(self, plotter, reference, index):
        point = _reference_point(reference)
        name = str(reference.get("name", "")).strip()
        if point is None or not name:
            return
        actor_name = f"datum-reference-preview-label-{index}"
        plotter.add_point_labels(
            np.asarray([point]),
            [name],
            name=actor_name,
            show_points=False,
            point_size=0,
            font_size=10,
            text_color=_LABEL_TEXT,
            shape_color=_LABEL_BACKGROUND,
            shape_opacity=.88,
            always_visible=True,
            render=False,
        )
        self._names.append(actor_name)


def _actor_for(scene, reference):
    kind = str(reference.get("kind", ""))
    instance_id = reference.get("instance_id") or None
    if kind in {"vertex", "edge", "face"}:
        dimension = {"vertex": 0, "edge": 1, "face": 2}[kind]
        collection = {
            0: scene.vertex_actors,
            1: scene.edge_actors,
            2: scene.face_actors,
        }[dimension]
        tag = reference.get("tag")
        for actor, actor_reference in collection.items():
            if (
                int(getattr(actor_reference, "dimension", -1)) == dimension
                and _same_optional(getattr(actor_reference, "instance_id", None), instance_id)
                and tag is not None
                and int(getattr(actor_reference, "tag", -1)) == int(tag)
            ):
                return actor, kind
        return None, kind

    if kind == "reference_point":
        actor = _entity_actor(scene.reference_actors, reference)
        return actor, kind
    if kind in {"datum_point", "datum_vector", "datum_plane"}:
        actor = _entity_actor(scene.datum_actors, reference)
        return actor, kind
    return None, kind


def _entity_actor(collection, reference):
    entity_id = reference.get("entity_id")
    instance_id = reference.get("instance_id") or None
    for actor, hit in collection.items():
        if (
            str(getattr(hit, "entity_id", "")) == str(entity_id or "")
            and _same_optional(getattr(hit, "instance_id", None), instance_id)
        ):
            return actor
    return None


def _same_optional(first, second):
    return (first or None) == (second or None)


def _reference_point(reference):
    value = reference.get("point") or reference.get("origin")
    if value is None and reference.get("points"):
        try:
            points = np.asarray(reference["points"], dtype=float)
            value = np.mean(points, axis=0)
        except (TypeError, ValueError):
            value = None
    if value is None:
        return None
    try:
        point = np.asarray(value, dtype=float).reshape(-1)
    except (TypeError, ValueError):
        return None
    if len(point) < 3 or not np.all(np.isfinite(point[:3])):
        return None
    return tuple(float(component) for component in point[:3])


def _style(actor, kind):
    actor.SetVisibility(True)
    prop = actor.GetProperty()
    mapper = actor.GetMapper()
    mapper.ScalarVisibilityOff()
    rgb = pv.Color(_HIGHLIGHT).float_rgb
    prop.SetColor(rgb)
    prop.SetLighting(False)
    if kind == "face":
        prop.SetOpacity(1.0)
        prop.SetEdgeVisibility(True)
        prop.SetEdgeColor(rgb)
        prop.SetLineWidth(3.0)
    elif kind == "edge":
        prop.SetOpacity(1.0)
        prop.SetLineWidth(7.0)
    elif kind in {"vertex", "reference_point", "datum_point"}:
        prop.SetOpacity(1.0)
        prop.SetPointSize(19.0)
    elif kind == "datum_plane":
        prop.SetOpacity(.36)
        prop.SetEdgeVisibility(True)
        prop.SetEdgeColor(rgb)
        prop.SetLineWidth(3.0)
    else:
        prop.SetOpacity(1.0)


def _restore(actor, state):
    actor.SetVisibility(state["visibility"])
    actor.SetPickable(state["pickable"])
    prop = actor.GetProperty()
    prop.SetColor(state["color"])
    prop.SetOpacity(state["opacity"])
    prop.SetLineWidth(state["line_width"])
    prop.SetPointSize(state["point_size"])
    prop.SetEdgeVisibility(state["edge_visibility"])
    prop.SetEdgeColor(state["edge_color"])
    prop.SetLighting(state["lighting"])
    actor.GetMapper().SetScalarVisibility(state["scalar_visibility"])
