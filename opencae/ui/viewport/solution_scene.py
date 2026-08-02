from .result_visualization import add_result
from .scene_camera import camera_position, restore_camera


def show_result(scene, result, field=None, options=None):
    camera = camera_position(scene.owner.plotter); scene.clear(render=False)
    try:
        scene.result_actor, scene.result_grid, scene.result_boundary_actor, scene.result_undeformed_actor = add_result(scene.owner.plotter, result, field, options)
    except Exception as exc:
        scene.owner.message.emit(f"Could not open solution: {exc}"); scene.owner.plotter.render(); return
    if camera is None: scene.owner.plotter.view_isometric(); scene.owner.plotter.reset_camera()
    else: restore_camera(scene.owner.plotter, camera)
    scene.owner.plotter.add_axes(color="#dce3e8"); scene.owner.result_query.configure((options or {}).get("query", ""), field); scene.owner.plotter.render()
