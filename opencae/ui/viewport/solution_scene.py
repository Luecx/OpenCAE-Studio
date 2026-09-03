"""Presents conventional solver results and job-backed topology frames."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np

from opencae.optimization import build_mesh_index
from opencae.ui.core.theme import PALETTE
from .result_visualization import add_result, update_result
from .scene_camera import camera_position, restore_camera


def show_result(scene, result, field=None, options=None):
    metadata = dict(getattr(result, "metadata", {}) or {})
    identity = _result_identity(result)
    previous_identity = getattr(scene, "_displayed_result_identity", None)
    is_topology = metadata.get("result_kind") == "topology_density"

    if is_topology:
        # The overlay clears its tracked actor names whenever Results is closed.
        # This lets reopening the same topology ResultSet frame again while frame
        # changes inside an already-visible result retain the current camera.
        topology_visible = bool(getattr(scene.topology_overlay, "_names", ()))
        _show_topology_result(
            scene,
            result,
            options or {},
            fit_on_load=identity != previous_identity or not topology_visible,
        )
        return

    options = options or {}
    animation = dict(options.get("_animation", {}) or {})
    if animation and scene.result_actor is not None and scene.result_grid is not None:
        try:
            grid = update_result(
                scene.result_actor,
                scene.result_mesh_actor,
                scene.result_boundary_actor,
                scene.result_undeformed_actor,
                result,
                field,
                options,
            )
        except Exception as exc:
            scene.owner.message.emit(f"Could not update animation frame: {exc}")
            grid = None
        if grid is not None:
            scene.result_grid = grid
            scene.owner.section_view.update_grid(
                grid,
                (
                    scene.result_actor,
                    scene.result_mesh_actor,
                    scene.result_boundary_actor,
                    scene.result_undeformed_actor,
                ),
            )
            scene.owner.plotter.render()
            return

    # A different ResultSet, or reopening a result after its actors were cleared,
    # is new visible content and should always start framed. Rebuilding the same
    # ResultSet for another field/range keeps the user's current camera.
    fit_on_load = identity != previous_identity or scene.result_actor is None
    camera = camera_position(scene.owner.plotter)
    scene.clear(render=False)
    try:
        (
            scene.result_actor,
            scene.result_grid,
            scene.result_mesh_actor,
            scene.result_boundary_actor,
            scene.result_undeformed_actor,
        ) = add_result(scene.owner.plotter, result, field, options)
    except Exception as exc:
        scene.owner.message.emit(f"Could not open solution: {exc}")
        scene.owner.plotter.render()
        return
    scene._displayed_result_identity = identity
    if fit_on_load or camera is None:
        scene.owner.plotter.view_isometric()
        scene.owner.plotter.reset_camera()
    else:
        restore_camera(scene.owner.plotter, camera)
    scene.owner.section_view.apply(
        options.get("section", {}),
        scene.result_grid,
        (
            scene.result_actor,
            scene.result_mesh_actor,
            scene.result_boundary_actor,
            scene.result_undeformed_actor,
        ),
    )
    scene.owner.plotter.add_axes(color=PALETTE["viewport_text"])
    scene.owner.result_query.configure(options.get("query", ""), field)
    scene.owner.plotter.render()


def _show_topology_result(scene, result, options, *, fit_on_load=False):
    frames = list(dict(result.metadata or {}).get("frames", ()))
    if not frames:
        scene.owner.message.emit("The topology result contains no saved iterations")
        return
    index = int(options.get("topology_frame_index", len(frames) - 1))
    index = min(max(index, 0), len(frames) - 1)
    frame = dict(frames[index])
    density_path = Path(str(frame.get("density_file", "")))
    if not density_path.exists():
        scene.owner.message.emit(
            f"Topology density frame is unavailable: {density_path}"
        )
        return
    try:
        with np.load(density_path, allow_pickle=False) as values:
            density = np.asarray(values["physical"], dtype=float).copy()
        mesh_index = build_mesh_index(scene.owner.store.project)
    except Exception as exc:
        scene.owner.message.emit(f"Could not open topology frame: {exc}")
        return
    fingerprint = str(dict(result.metadata or {}).get("mesh_fingerprint", ""))
    if fingerprint and fingerprint != mesh_index.fingerprint:
        scene.owner.message.emit(
            "The current mesh differs from the mesh used by this Study job"
        )
        return

    camera = camera_position(scene.owner.plotter)
    scene.clear(render=False)
    scene.owner.display_mode = "mesh"
    scene.owner.toolbar.set_display("mesh")
    scene._show_assembly()
    iteration = SimpleNamespace(
        number=int(frame.get("number", index + 1)),
        objective_value=float(frame.get("objective", 0.0)),
        maximum_density_change=float(
            frame.get("maximum_density_change", 0.0)
        ),
    )
    run = SimpleNamespace(name=getattr(result, "name", "Topology Result"))
    topology_actors = scene.topology_overlay.show(
        scene.owner,
        run,
        iteration,
        mesh_index,
        density,
        threshold=0.0,
        options=options,
    )
    if topology_actors is not None:
        actor, grid, mesh_actor, boundary_actor = topology_actors
        scene.owner.section_view.apply(
            options.get("section", {}),
            grid,
            (actor, mesh_actor, boundary_actor),
        )
    scene._displayed_result_identity = _result_identity(result)
    if fit_on_load or camera is None:
        scene.owner.plotter.view_isometric()
        scene.owner.plotter.reset_camera()
    else:
        restore_camera(scene.owner.plotter, camera)
    scene.owner.result_query.configure("")
    scene.owner.plotter.render()


def _result_identity(result):
    """Return a stable display identity even for external non-persisted results."""
    identifier = str(getattr(result, "id", "") or "").strip()
    if identifier:
        return identifier
    source = str(getattr(result, "source_file", "") or "").strip()
    return source or f"object:{id(result)}"
