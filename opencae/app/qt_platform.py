"""Select optional Qt platform overrides before QApplication is constructed.

PyVistaQt's QOpenGLWidget/vtkGenericOpenGLRenderWindow integration owns the
OpenGL surface through Qt and no longer passes a native window handle to VTK.
OpenCAE therefore lets Qt choose its native QPA backend by default, including
Wayland on Linux. Explicit ``QT_QPA_PLATFORM`` and ``OPENCAE_QT_PLATFORM``
overrides remain available for driver/platform troubleshooting.
"""

from __future__ import annotations

import os
from collections.abc import MutableMapping


_OPENCAE_PLATFORM_ENV = "OPENCAE_QT_PLATFORM"
_QT_PLATFORM_ENV = "QT_QPA_PLATFORM"
_NATIVE_VALUES = {"auto", "native", "system"}
_SUPPORTED_OVERRIDES = _NATIVE_VALUES | {"xcb", "wayland"}


def is_wayland_session(environment: MutableMapping[str, str] | None = None) -> bool:
    """Return whether the process appears to run inside a Wayland session."""
    env = os.environ if environment is None else environment
    session_type = str(env.get("XDG_SESSION_TYPE", "")).strip().casefold()
    return session_type == "wayland" or bool(str(env.get("WAYLAND_DISPLAY", "")).strip())


def recommended_qt_platform(
    *,
    system: str | None = None,
    environment: MutableMapping[str, str] | None = None,
) -> str | None:
    """Return an explicit Qt QPA backend only when the user requested one.

    ``None`` means Qt chooses its normal native platform plugin. The ``system``
    argument is retained for API/test compatibility but no longer affects auto
    selection: Wayland sessions are intentionally not forced through XWayland.
    """
    del system
    env = os.environ if environment is None else environment

    # Respect the standard Qt override first. This also lets CI use ``offscreen``
    # without OpenCAE replacing it with a desktop platform plugin.
    if str(env.get(_QT_PLATFORM_ENV, "")).strip():
        return None

    requested = str(env.get(_OPENCAE_PLATFORM_ENV, "auto")).strip().casefold() or "auto"
    if requested not in _SUPPORTED_OVERRIDES:
        raise ValueError(
            f"Unsupported {_OPENCAE_PLATFORM_ENV}={requested!r}; expected one of "
            f"{', '.join(sorted(_SUPPORTED_OVERRIDES))}"
        )
    if requested in _NATIVE_VALUES:
        return None
    return requested


def configure_qt_platform_environment() -> str | None:
    """Apply an explicit OpenCAE Qt platform override before Qt is imported."""
    backend = recommended_qt_platform()
    if backend is not None:
        os.environ[_QT_PLATFORM_ENV] = backend
    return backend
