from __future__ import annotations

import math
import numpy as np


def world_size_for_pixels(plotter, point, pixels):
    camera = plotter.camera
    height = max(int(plotter.window_size[1]), 1)
    if camera.GetParallelProjection():
        return max(2.0 * camera.GetParallelScale() * float(pixels) / height, 1e-9)
    position = np.asarray(camera.position, dtype=float)
    distance = max(float(np.linalg.norm(np.asarray(point, dtype=float) - position)), 1e-9)
    angle = math.radians(float(camera.GetViewAngle()))
    return max(2.0 * distance * math.tan(angle * 0.5) * float(pixels) / height, 1e-9)
