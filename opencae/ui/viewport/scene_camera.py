from __future__ import annotations

import logging

import numpy as np

LOGGER = logging.getLogger(__name__)


def camera_position(plotter):
    try:
        return plotter.camera_position
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None
    except Exception:
        LOGGER.exception("Unexpected failure while reading viewport camera")
        return None


def restore_camera(plotter, camera):
    if camera is None:
        return False
    try:
        plotter.camera_position = camera
        plotter.reset_camera_clipping_range()
        return True
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return False
    except Exception:
        LOGGER.exception("Unexpected failure while restoring viewport camera")
        return False


def fit_camera(
    plotter,
    *,
    points=None,
    reset_orientation: bool = False,
    render: bool = True,
) -> bool:
    """Frame visible content robustly, including degenerate 1D/2D datasets.

    Normal Fit View preserves the user's viewing direction.  A geometry-aware
    fallback only changes orientation when a line is viewed almost end-on or a
    planar dataset almost edge-on.  Initial-load callers may request a fresh
    orientation explicitly.
    """
    raw_points = _finite_points(points)
    bounds = _fit_bounds(plotter, raw_points)
    if bounds is None:
        return False

    frame = _principal_frame(raw_points)
    direction = None
    viewup = None
    if frame is not None:
        rank, primary, normal = frame
        if reset_orientation:
            direction, viewup = _fresh_view(rank, primary, normal)
        elif _needs_degenerate_reorientation(plotter, rank, primary, normal):
            direction, viewup = _fresh_view(rank, primary, normal)

    try:
        if direction is not None:
            plotter.view_vector(
                direction,
                viewup=viewup,
                render=False,
                bounds=bounds,
            )
        else:
            plotter.reset_camera(render=False, bounds=bounds)
        plotter.reset_camera_clipping_range()
        if render:
            plotter.render()
        return True
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return False
    except Exception:
        LOGGER.exception("Unexpected failure while fitting viewport camera")
        return False


def _finite_points(points):
    if points is None:
        return None
    try:
        values = np.asarray(points, dtype=float)
    except (TypeError, ValueError):
        return None
    if values.ndim != 2 or values.shape[1] != 3 or not len(values):
        return None
    finite = values[np.all(np.isfinite(values), axis=1)]
    return finite if len(finite) else None


def _fit_bounds(plotter, points=None):
    if points is not None and len(points):
        minimum = np.min(points, axis=0)
        maximum = np.max(points, axis=0)
        bounds = np.asarray(
            (
                minimum[0], maximum[0],
                minimum[1], maximum[1],
                minimum[2], maximum[2],
            ),
            dtype=float,
        )
    else:
        try:
            bounds = np.asarray(plotter.compute_bounds(), dtype=float)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return None
        except Exception:
            LOGGER.exception("Unexpected failure while computing viewport bounds")
            return None

    if bounds.shape != (6,) or not np.all(np.isfinite(bounds)):
        return None
    minimum = bounds[::2].copy()
    maximum = bounds[1::2].copy()
    if np.any(maximum < minimum):
        return None

    spans = maximum - minimum
    largest = float(np.max(spans))
    center = 0.5 * (minimum + maximum)
    if largest <= 1.0e-14:
        # Point-only content still needs a finite camera volume.  Keep this
        # local rather than scaling with the absolute world-coordinate offset.
        padding = 0.5
        minimum = center - padding
        maximum = center + padding
    else:
        # VTK's camera reset can produce fragile clipping/distance values when
        # one or more axes have exactly zero extent. Give line/plane datasets a
        # tiny thickness while leaving their meaningful dimensions untouched.
        padding = max(largest * 0.02, 1.0e-12)
        threshold = max(largest * 1.0e-10, 1.0e-14)
        for axis in range(3):
            if spans[axis] <= threshold:
                minimum[axis] -= padding
                maximum[axis] += padding

    return (
        float(minimum[0]), float(maximum[0]),
        float(minimum[1]), float(maximum[1]),
        float(minimum[2]), float(maximum[2]),
    )


def _principal_frame(points):
    if points is None or len(points) < 2:
        return None
    centered = np.asarray(points, dtype=float) - np.mean(points, axis=0)
    try:
        _u, singular, vh = np.linalg.svd(centered, full_matrices=True)
    except np.linalg.LinAlgError:
        return None
    if not len(singular) or float(singular[0]) <= 1.0e-14:
        return None
    tolerance = max(float(singular[0]) * 1.0e-8, 1.0e-14)
    rank = int(np.count_nonzero(singular > tolerance))
    primary = _normalized(vh[0])
    normal = _normalized(vh[-1]) if rank == 2 and vh.shape[0] >= 3 else None
    return rank, primary, normal


def _fresh_view(rank, primary, normal):
    if rank <= 1 and primary is not None:
        # Pick the world axis least aligned with the line. This maximizes its
        # projected length and avoids the classic two-node beam disappearing
        # when an isometric direction happens to match the element direction.
        candidates = np.eye(3)
        direction = min(candidates, key=lambda axis: abs(float(np.dot(axis, primary))))
        viewup = _safe_viewup(direction, preferred=primary)
        return tuple(direction), tuple(viewup)
    if rank == 2 and normal is not None:
        direction = normal
        viewup = _safe_viewup(direction, preferred=primary)
        return tuple(direction), tuple(viewup)
    direction = _normalized(np.asarray((1.0, 1.0, 1.0), dtype=float))
    return tuple(direction), (0.0, 0.0, 1.0)


def _needs_degenerate_reorientation(plotter, rank, primary, normal) -> bool:
    try:
        camera_direction = _normalized(np.asarray(plotter.camera.direction, dtype=float))
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return False
    if camera_direction is None:
        return False
    if rank <= 1 and primary is not None:
        return abs(float(np.dot(camera_direction, primary))) >= 0.94
    if rank == 2 and normal is not None:
        # Dot ~= 0 means the camera direction lies in the plane: an edge-on view.
        return abs(float(np.dot(camera_direction, normal))) <= 0.12
    return False


def _safe_viewup(direction, preferred=None):
    direction = _normalized(direction)
    if direction is None:
        return np.asarray((0.0, 0.0, 1.0), dtype=float)
    if preferred is not None:
        preferred = _normalized(preferred)
        if preferred is not None and abs(float(np.dot(direction, preferred))) < 0.95:
            return preferred
    for candidate in (
        np.asarray((0.0, 0.0, 1.0), dtype=float),
        np.asarray((0.0, 1.0, 0.0), dtype=float),
        np.asarray((1.0, 0.0, 0.0), dtype=float),
    ):
        if abs(float(np.dot(direction, candidate))) < 0.95:
            return candidate
    return np.asarray((0.0, 1.0, 0.0), dtype=float)


def _normalized(vector):
    if vector is None:
        return None
    values = np.asarray(vector, dtype=float)
    length = float(np.linalg.norm(values))
    if not np.isfinite(length) or length <= 1.0e-14:
        return None
    return values / length
