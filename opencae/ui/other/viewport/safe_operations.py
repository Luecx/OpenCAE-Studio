from __future__ import annotations

import logging

LOGGER = logging.getLogger(__name__)

_EXPECTED_VTK_ERRORS = (AttributeError, KeyError, RuntimeError, TypeError, ValueError)


def remove_actor(plotter, name: str, *, render: bool = False) -> bool:
    """Remove a named actor without hiding unexpected renderer failures."""
    try:
        plotter.remove_actor(name, reset_camera=False, render=render)
        return True
    except _EXPECTED_VTK_ERRORS:
        return False
    except Exception:
        LOGGER.exception("Unexpected failure while removing viewport actor %s", name)
        return False


def disable_picking(plotter) -> bool:
    try:
        plotter.disable_picking()
        return True
    except _EXPECTED_VTK_ERRORS:
        return False
    except Exception:
        LOGGER.exception("Unexpected failure while disabling viewport picking")
        return False


def add_interaction_observer(interactor, event: str, callback) -> bool:
    try:
        interactor.add_observer(event, callback)
        return True
    except _EXPECTED_VTK_ERRORS:
        return False
    except Exception:
        LOGGER.exception("Unexpected failure while installing viewport observer %s", event)
        return False
