from __future__ import annotations

import numpy as np


def rotation_matrix(rotation):
    rx, ry, rz = np.radians(np.asarray(rotation, dtype=float))
    sx, cx = np.sin(rx), np.cos(rx)
    sy, cy = np.sin(ry), np.cos(ry)
    sz, cz = np.sin(rz), np.cos(rz)
    mx = np.array(((1, 0, 0), (0, cx, -sx), (0, sx, cx)), dtype=float)
    my = np.array(((cy, 0, sy), (0, 1, 0), (-sy, 0, cy)), dtype=float)
    mz = np.array(((cz, -sz, 0), (sz, cz, 0), (0, 0, 1)), dtype=float)
    return mz @ my @ mx


def transform_points(points, instance):
    matrix = rotation_matrix(instance.rotation)
    offset = np.asarray(instance.translation, dtype=float)
    values = np.asarray(points, dtype=float)
    return values @ matrix.T + offset


def transform_vector(vector, instance):
    return rotation_matrix(instance.rotation) @ np.asarray(vector, dtype=float)
