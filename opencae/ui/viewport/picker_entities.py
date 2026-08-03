from __future__ import annotations

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from opencae.model.selection import SelectableKind, SelectionOperation, ViewportHit
from .assembly_context import ActorReference
from .instance_transform import transform_points


def additive_selection():
    return bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier)


def selection_operation() -> SelectionOperation:
    modifiers = QApplication.keyboardModifiers()
    if modifiers & Qt.KeyboardModifier.ControlModifier:
        return SelectionOperation.REMOVE
    if modifiers & Qt.KeyboardModifier.ShiftModifier:
        return SelectionOperation.ADD
    return SelectionOperation.REPLACE


def actor_kind(scene, actor):
    if actor in scene.edge_actors:
        return "edge"
    if actor in scene.vertex_actors:
        return "vertex"
    if actor in scene.reference_actors:
        return "rp"
    if actor in scene.datum_actors:
        value = scene.datum_actors[actor]
        if isinstance(value, ViewportHit):
            return value.kind.value
        return "datum"
    return "face"


def actor_entity(scene, actor, mode=None):
    """Return a typed hit for a geometry, datum or reference-point actor."""
    for collection in (scene.edge_actors, scene.vertex_actors, scene.face_actors, scene.reference_actors, scene.datum_actors):
        if actor not in collection:
            continue
        reference = collection[actor]
        if isinstance(reference, ViewportHit):
            return reference
        kind = actor_kind(scene, actor)
        dimension = {"vertex": 0, "edge": 1, "face": 2, "cell": 3}.get(kind, -1)
        if not isinstance(reference, ActorReference):
            reference = ActorReference(None, dimension, int(reference))
        point = _geometry_position(scene, reference, kind)
        selectable = {
            "vertex": SelectableKind.GEOMETRY_VERTEX,
            "edge": SelectableKind.GEOMETRY_EDGE,
            "face": SelectableKind.GEOMETRY_FACE,
            "cell": SelectableKind.GEOMETRY_CELL,
            "datum_point": SelectableKind.DATUM_POINT,
        }.get(kind, SelectableKind.GEOMETRY_FACE)
        return ViewportHit(
            kind=selectable,
            instance_id=reference.instance_id,
            topology_tag=reference.tag if dimension >= 0 else None,
            world_position=point,
            dimension=reference.dimension,
            label=reference.label,
        )
    return None


def _geometry_position(scene, reference, kind):
    snapshot = scene.snapshot_for(reference.instance_id)
    if snapshot is None:
        return None
    points = None
    if kind == "vertex":
        patch = next((item for item in snapshot.vertices if item.tag == reference.tag), None)
        points = np.asarray([patch.point]) if patch else None
    elif kind == "edge":
        patch = next((item for item in snapshot.edges if item.tag == reference.tag), None)
        points = np.asarray(patch.points) if patch else None
    elif kind == "face":
        patch = next((item for item in snapshot.surfaces if item.tag == reference.tag), None)
        points = np.asarray(patch.points) if patch else None
    if points is None or not len(points):
        return None
    instance = scene.instance_for(reference.instance_id)
    if instance:
        points = transform_points(points, instance)
    return tuple(np.mean(points, axis=0))
