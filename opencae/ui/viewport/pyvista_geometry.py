"""Build and style persistent CAD topology actors for the PyVista scene."""

from __future__ import annotations

import numpy as np
import pyvista as pv

from opencae.geometry.meshability import surface_classification
from opencae.ui.core.theme import PALETTE
from .assembly_context import ActorReference
from .geometry_render_cache import GEOMETRY_RENDER_CACHE
from .instance_transform import rotation_matrix, transform_points
from .surface_shading import face_color

_BASE_COLORS = {}


def add_geometry(
    plotter,
    snapshot,
    instance=None,
    *,
    color_by_meshability=True,
    hidden_faces=(),
    hidden_cells=(),
):
    """Add persistent CAD actors with prepared render meshes and neutral shading.

    Expensive local-space ``clean`` and normal creation is cached per geometry
    fingerprint. Assembly instances copy those prepared datasets and apply only
    their rigid transform, avoiding repeated VTK filter work on every stage or
    Geometry/Mesh context switch.

    ``hidden_faces`` and ``hidden_cells`` are display-only topology filters.
    Actors are deliberately still created for hidden faces so subsequent
    visibility edits can toggle existing VTK props instead of rebuilding the
    complete geometry pipeline.
    """
    _configure_geometry_light(plotter)
    hidden_face_tags = {int(value) for value in hidden_faces}
    hidden_cell_tags = {int(value) for value in hidden_cells}
    prepared_faces, prepared_edges, prepared_vertices = (
        GEOMETRY_RENDER_CACHE.prepared(snapshot)
    )
    faces, edges, vertices = {}, {}, {}
    prefix = f"{instance.name}-" if instance else ""
    visible_surface_count = 0

    for patch in snapshot.surfaces:
        hidden = _surface_hidden(
            snapshot,
            patch.tag,
            hidden_face_tags,
            hidden_cell_tags,
        )
        if not hidden:
            visible_surface_count += 1
        mesh = _instance_mesh(
            prepared_faces[int(patch.tag)],
            instance,
            rotate_normals=True,
        )
        classification = (
            surface_classification(snapshot, patch.tag)
            if color_by_meshability
            else None
        )
        color = (
            face_color(classification)
            if classification is not None
            else PALETTE["cad_face"]
        )
        actor = plotter.add_mesh(
            mesh,
            color=color,
            show_edges=False,
            lighting=True,
            smooth_shading=True,
            ambient=0.88,
            diffuse=0.12,
            specular=0.0,
            specular_power=1.0,
            pickable=True,
            name=f"{prefix}face-{patch.tag}",
            render=False,
        )
        actor.SetVisibility(not hidden)
        try:
            prop = actor.GetProperty()
            prop.SetLighting(True)
            prop.SetInterpolationToPhong()
            prop.SetAmbient(0.88)
            prop.SetDiffuse(0.12)
            prop.SetSpecular(0.0)
            prop.SetSpecularPower(1.0)
            # CAD faces are triangulated internally for rendering, but those
            # tessellation edges are not model topology and must never masquerade
            # as an FE mesh when a face highlight enables edge visibility.
            prop.SetEdgeVisibility(False)
            set_edge_opacity = getattr(prop, "SetEdgeOpacity", None)
            if set_edge_opacity is not None:
                set_edge_opacity(0.0)
        except (AttributeError, RuntimeError):
            pass
        actor.GetProperty().BackfaceCullingOff()
        actor.GetProperty().FrontfaceCullingOff()
        _BASE_COLORS[actor] = color
        faces[actor] = ActorReference(
            instance.id if instance else None,
            2,
            patch.tag,
            instance.name if instance else "",
        )

    # Topology curves remain available as persistent props as well. Their
    # visibility follows whether at least one surface of the part is visible,
    # matching the old behavior without deleting/recreating the actors.
    topology_visible = bool(visible_surface_count)
    for patch in snapshot.edges:
        mesh = _instance_mesh(
            prepared_edges[int(patch.tag)],
            instance,
            rotate_normals=False,
        )
        actor = plotter.add_mesh(
            mesh,
            color=PALETTE["cad_edge"],
            line_width=3.6,
            lighting=False,
            render_lines_as_tubes=True,
            pickable=True,
            name=f"{prefix}edge-{patch.tag}",
            render=False,
        )
        actor.SetVisibility(topology_visible)
        _configure_edge_mapper(actor)
        edges[actor] = ActorReference(
            instance.id if instance else None,
            1,
            patch.tag,
            instance.name if instance else "",
        )

    for patch in snapshot.vertices:
        mesh = _instance_mesh(
            prepared_vertices[int(patch.tag)],
            instance,
            rotate_normals=False,
        )
        actor = plotter.add_mesh(
            mesh,
            color=PALETTE["cad_vertex"],
            point_size=8.0,
            render_points_as_spheres=True,
            lighting=False,
            pickable=True,
            name=f"{prefix}vertex-{patch.tag}",
            render=False,
        )
        # Vertex visibility is normally controlled by the active picker. Start
        # hidden so a scene cannot flash topology points before configure().
        actor.SetVisibility(False)
        vertices[actor] = ActorReference(
            instance.id if instance else None,
            0,
            patch.tag,
            instance.name if instance else "",
        )
    return faces, edges, vertices


def set_actor_selected(actor, selected: bool, kind: str = "face"):
    """Apply or remove the canonical selection style from one topology actor."""
    base = _BASE_COLORS.get(
        actor,
        {
            "face": PALETTE["cad_face"],
            "edge": PALETTE["cad_edge"],
            "vertex": PALETTE["cad_vertex"],
            "rp": PALETTE["reference_point"],
        }.get(kind, PALETTE["cad_face"]),
    )
    color = PALETTE["selection_3d"] if selected else base
    rgb = color if isinstance(color, tuple) else pv.Color(color).float_rgb
    actor.GetProperty().SetColor(rgb)
    if kind == "edge":
        actor.GetProperty().SetLineWidth(5.5 if selected else 3.6)
    if kind == "vertex":
        actor.GetProperty().SetPointSize(13.0 if selected else 8.0)
    if kind == "rp":
        actor.GetProperty().SetPointSize(20.0 if selected else 15.0)


def forget_actor_colors(actors) -> None:
    """Release scene-owned actor keys from the base-color registry on clear."""
    for actor in tuple(actors or ()):
        _BASE_COLORS.pop(actor, None)


def surface_is_hidden(snapshot, tag, hidden_faces, hidden_cells) -> bool:
    """Return whether face/cell visibility state hides one CAD surface."""
    return _surface_hidden(snapshot, tag, hidden_faces, hidden_cells)


def _instance_mesh(mesh, instance, *, rotate_normals: bool):
    """Return a rigidly transformed copy while preserving prepared topology data."""
    if instance is None:
        return mesh
    result = mesh.copy(deep=True)
    result.points = transform_points(result.points, instance)
    if rotate_normals:
        matrix = rotation_matrix(instance.rotation)
        for attributes in (result.point_data, result.cell_data):
            if "Normals" not in attributes:
                continue
            normals = np.asarray(attributes["Normals"], dtype=float)
            attributes["Normals"] = normals @ matrix.T
    return result


def _surface_hidden(snapshot, tag, hidden_faces, hidden_cells):
    surface_tag = int(tag)
    if surface_tag in hidden_faces:
        return True
    adjacent = {
        int(value)
        for value in getattr(snapshot, "surface_to_cells", {}).get(
            surface_tag,
            (),
        )
    }
    return bool(adjacent and adjacent.issubset(hidden_cells))


def _configure_geometry_light(plotter) -> None:
    """Install one neutral camera light for restrained Lambert shading."""
    try:
        from vtkmodules.vtkRenderingCore import vtkLight

        renderer = plotter.renderer
        renderer.RemoveAllLights()
        automatic = getattr(renderer, "AutomaticLightCreationOff", None)
        if automatic is not None:
            automatic()
        follow_camera = getattr(renderer, "LightFollowCameraOn", None)
        if follow_camera is not None:
            follow_camera()
        two_sided = getattr(renderer, "SetTwoSidedLighting", None)
        if two_sided is not None:
            two_sided(True)

        light = vtkLight()
        light.SetLightTypeToCameraLight()
        light.SetPosition(0.65, -0.45, 1.0)
        light.SetFocalPoint(0.0, 0.0, 0.0)
        light.SetColor(1.0, 1.0, 1.0)
        light.SetIntensity(1.0)
        light.SetPositional(False)
        light.SwitchOn()
        renderer.AddLight(light)
    except (AttributeError, ImportError, RuntimeError, TypeError):
        return


def _configure_edge_mapper(actor) -> None:
    """Use tube-rendered CAD polylines with normal depth testing."""
    try:
        mapper = actor.GetMapper()
        mapper.SetResolveCoincidentTopologyToOff()
    except (AttributeError, RuntimeError, TypeError):
        pass
    try:
        actor.GetProperty().SetRenderLinesAsTubes(True)
    except (AttributeError, RuntimeError):
        pass
