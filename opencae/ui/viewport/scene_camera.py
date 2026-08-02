def camera_position(plotter):
    try: return plotter.camera_position
    except Exception: return None


def restore_camera(plotter, camera):
    try:
        plotter.camera_position = camera
        plotter.reset_camera_clipping_range()
    except Exception:
        pass
