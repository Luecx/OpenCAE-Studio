from __future__ import annotations

import numpy as np


def coordinate_point(p):
    local = xyz(p, "coordinate"); system = p.get("coordinate_system") or {}
    origin = np.asarray(system.get("origin", (0, 0, 0)), float); x = unit(system.get("axis_1", (1, 0, 0)))
    y0 = np.asarray(system.get("axis_2", (0, 1, 0)), float); y = unit(y0 - np.dot(y0, x) * x); z = unit(np.cross(x, y))
    if str(system.get("system_type", "")).lower().startswith("cyl"):
        r, theta, height = local; angle = np.deg2rad(theta)
        return origin + r * np.cos(angle) * x + r * np.sin(angle) * y + height * z
    return origin + local[0] * x + local[1] * y + local[2] * z


def edge_parameter(points, p):
    value = float(p.get("position", .5)); definition = p.get("definition", "Normalized parameter")
    total = float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())
    if definition == "Arc length from start": return 0.0 if total <= 1e-14 else value / total
    if definition == "Arc length from end": return 1.0 if total <= 1e-14 else 1.0 - value / total
    return value


def ref_point(ref):
    if not ref: raise ValueError("A point reference is required")
    return np.asarray(ref.get("point") or ref.get("origin"), dtype=float)


def ref_direction(ref):
    if not ref: raise ValueError("A direction reference is required")
    if ref.get("direction") is not None: return np.asarray(ref["direction"], dtype=float)
    if ref.get("normal") is not None: return np.asarray(ref["normal"], dtype=float)
    points = ref.get("points") or ()
    return np.asarray(points[-1], dtype=float) - np.asarray(points[0], dtype=float) if len(points) >= 2 else np.asarray((1, 0, 0), dtype=float)


def ref_curve(ref):
    if not ref or not ref.get("points"): raise ValueError("An edge reference is required")
    return np.asarray(ref["points"], dtype=float)


def xyz(values, prefix): return np.asarray([values.get(f"{prefix}_{axis}", 0.0) for axis in "xyz"], dtype=float)

def unit(value):
    vector = np.asarray(value, dtype=float); norm = float(np.linalg.norm(vector))
    if norm < 1e-14: raise ValueError("Direction vectors must be non-zero")
    return vector / norm

def polyline_point(points, value):
    value = min(1.0, max(0.0, value)); lengths = np.linalg.norm(np.diff(points, axis=0), axis=1); total = lengths.sum()
    if total <= 1e-14: return points[0]
    target = value * total; index = min(int(np.searchsorted(np.cumsum(lengths), target)), len(lengths) - 1)
    before = lengths[:index].sum(); return points[index] + (target - before) / max(lengths[index], 1e-14) * (points[index + 1] - points[index])
def polyline_tangent(points, value):
    lengths = np.linalg.norm(np.diff(points, axis=0), axis=1); target = min(1.0, max(0.0, value)) * lengths.sum()
    index = min(int(np.searchsorted(np.cumsum(lengths), target)), len(lengths) - 1); return unit(points[index + 1] - points[index])
def plane_axis(normal):
    seed = np.array((1.0, 0.0, 0.0)) if abs(normal[0]) < 0.85 else np.array((0.0, 1.0, 0.0))
    return unit(seed - np.dot(seed, normal) * normal)
