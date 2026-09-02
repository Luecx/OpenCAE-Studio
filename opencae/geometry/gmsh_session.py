from __future__ import annotations

from contextlib import contextmanager
from threading import RLock
import logging

from .errors import GeometryError

_LOCK = RLock()
_LOG = logging.getLogger(__name__)


@contextmanager
def gmsh_model(name: str):
    try:
        import gmsh
    except ImportError as exc:
        raise GeometryError(
            "Gmsh is not installed. Run: python -m pip install gmsh"
        ) from exc
    with _LOCK:
        initialized_here = False
        try:
            try:
                initialized = bool(gmsh.isInitialized())
            except AttributeError:
                initialized = False
            if not initialized:
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
