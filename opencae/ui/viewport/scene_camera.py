from __future__ import annotations

import logging

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
    if camera is None: return False
    try:
        plotter.camera_position = camera
        plotter.reset_camera_clipping_range()
        return True
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return False
    except Exception:
        LOGGER.exception("Unexpected failure while restoring viewport camera")
        return False
