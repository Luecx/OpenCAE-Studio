from __future__ import annotations

from contextlib import contextmanager
from threading import RLock
import logging

from .errors import GeometryError

_LOCK = RLock()
_LOG = logging.getLogger(__name__)


def _gmsh_module():
    try:
        import gmsh
    except ImportError as exc:
        raise GeometryError(
            "Gmsh is not installed. Run: python -m pip install gmsh"
        ) from exc
    return gmsh


def _is_initialized(gmsh) -> bool:
    try:
        return bool(gmsh.isInitialized())
    except AttributeError:
        return False


def initialize_gmsh() -> bool:
    """Initialize Gmsh once on the caller thread and keep it alive.

    The desktop application calls this during splash-screen startup on the Qt
    main thread. Gmsh may touch process-global/native state during initialize;
    doing that lazily from a meshing worker can fail on some platforms with a
    main-thread diagnostic. Keeping the initialized session alive also avoids
    repeatedly tearing down that global state between mesh operations.
    """
    try:
        gmsh = _gmsh_module()
    except GeometryError:
        return False
    with _LOCK:
        if not _is_initialized(gmsh):
            gmsh.initialize()
        gmsh.option.setNumber("General.Terminal", 0)
    return True


def finalize_gmsh() -> None:
    """Release the process-wide Gmsh session during application shutdown."""
    try:
        gmsh = _gmsh_module()
    except GeometryError:
        return
    with _LOCK:
        if not _is_initialized(gmsh):
            return
        try:
            gmsh.clear()
        except Exception as exc:
            _LOG.debug("Gmsh cleanup failed: %s", exc, exc_info=True)
        try:
            gmsh.finalize()
        except Exception as exc:
            _LOG.debug("Gmsh finalization failed: %s", exc, exc_info=True)


@contextmanager
def gmsh_model(name: str):
    gmsh = _gmsh_module()
    with _LOCK:
        initialized_here = False
        try:
            if not _is_initialized(gmsh):
                # Non-GUI callers retain the old self-contained behavior. The
                # desktop path normally arrives here already initialized by the
                # main thread during startup.
                gmsh.initialize()
                initialized_here = True
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.clear()
            gmsh.model.add(name)
            yield gmsh
        except GeometryError:
            raise
        except Exception as exc:
            raise GeometryError(str(exc)) from exc
        finally:
            try:
                gmsh.clear()
            except Exception as exc:
                _LOG.debug("Gmsh cleanup failed: %s", exc, exc_info=True)
            if initialized_here:
                try:
                    gmsh.finalize()
                except Exception as exc:
                    _LOG.debug("Gmsh finalization failed: %s", exc, exc_info=True)
