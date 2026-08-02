import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from .assembly_context import ActorReference
from .instance_transform import transform_points


def additive_selection(): return bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier)

def actor_kind(scene, actor):
    if actor in scene.edge_actors: return "edge"
    if actor in scene.vertex_actors: return "vertex"
    if actor in scene.reference_actors: return "rp"
    if actor in scene.datum_actors: return scene.datum_actors[actor].get("kind","datum")
    return "face"

def actor_entity(scene, actor, mode=None):
    for collection in (scene.edge_actors,scene.vertex_actors,scene.face_actors,scene.reference_actors,scene.datum_actors):
        if actor not in collection: continue
        reference = collection[actor]
        if isinstance(reference,dict): return dict(reference)
        kind = actor_kind(scene,actor); dim = {"vertex":0,"edge":1,"face":2}.get(kind,-1)
        if not isinstance(reference,ActorReference): reference = ActorReference(None,dim,int(reference))
        result = {"name":reference.label,"kind":kind,"dimension":reference.dimension,"tag":reference.tag,"instance":reference.instance_name}
        _add_geometry_data(scene,result); return result
    return None

def _add_geometry_data(scene, result):
    snapshot = scene.snapshot_for(result.get("instance")); tag = result.get("tag"); kind = result.get("kind")
    if snapshot is None: return
    instance = scene.instance_for(result.get("instance")); points = None
    if kind == "vertex":
        patch = next((item for item in snapshot.vertices if item.tag == tag),None); points = np.asarray([patch.point]) if patch else None
    elif kind == "edge":
        patch = next((item for item in snapshot.edges if item.tag == tag),None); points = np.asarray(patch.points) if patch else None
    elif kind == "face":
        patch = next((item for item in snapshot.surfaces if item.tag == tag),None); points = np.asarray(patch.points) if patch else None
    if points is None or not len(points): return
    if instance: points = transform_points(points,instance)
    result["point"] = tuple(np.mean(points,axis=0)); result["points"] = [tuple(row) for row in points]
    if kind == "face" and len(points) >= 3:
        normal = np.cross(points[1]-points[0],points[2]-points[0]); norm = np.linalg.norm(normal)
        if norm > 1e-14: result["normal"] = tuple(normal/norm)
