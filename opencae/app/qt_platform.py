"""Selects a safe Qt platform backend before QApplication is constructed.

OpenCAE currently embeds VTK through ``pyvistaqt.QtInteractor``. That widget is
built on the Python ``QVTKRenderWindowInteractor`` path, which hands a native Qt
window id to a platform-specific ``vtkRenderWindow``. On Linux, VTK normally
tries the X11 OpenGL render window first. A native Wayland Qt window id is not an
X11 window id, so mixing both backends can fail with ``BadWindow``.

Until the viewport is migrated to a Qt-owned generic OpenGL integration, the
safe production default for Wayland sessions is therefore Qt's ``xcb`` backend.
Explicit user/developer platform choices are always respected.
"""

from __future__ import annotations

import os
import platform
from collections.abc import MutableMapping


_OPENCAE_PLATFORM_ENV = "OPENCAE_QT_PLATFORM"
_QT_PLATFORM_ENV = "QT_QPA_PLATFORM"
_NATIVE_VALUES = {"native", "system"}
_SUPPORTED_OVERRIDES = {"auto", "native", "system", "xcb", "wayland"}


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
    """Return the Qt QPA backend OpenCAE should request, if any.

    ``None`` means that Qt should choose its normal platform backend. An
    explicitly supplied ``QT_QPA_PLATFORM`` always wins. ``OPENCAE_QT_PLATFORM``
    is intended for OpenCAE-specific testing and may be ``auto``, ``native``,
    ``system``, ``xcb`` or ``wayland``.
    """
    env = os.environ if environment is None else environment

    # Respect the standard Qt override first. Users who deliberately launch with
    # QT_QPA_PLATFORM=wayland must be able to test the native path unchanged.
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
    if requested in {"xcb", "wayland"}:
        return requested

    current_system = (system or platform.system()).casefold()
    if current_system == "linux" and is_wayland_session(env):
        # The current PyVistaQt bridge still creates a platform vtkRenderWindow
        # and feeds it a Qt native window id. Keeping Qt on X11/XWayland avoids
        # passing a Wayland handle into vtkXOpenGLRenderWindow.
        return "xcb"
    return None


def configure_qt_platform_environment() -> str | None:
    """Apply OpenCAE's Qt platform recommendation before QApplication exists."""
    backend = recommended_qt_platform()
    if backend is not None:
        os.environ[_QT_PLATFORM_ENV] = backend
    return backend
