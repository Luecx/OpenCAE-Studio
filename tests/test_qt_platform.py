"""Tests OpenCAE's pre-QApplication Qt platform and OpenGL policy."""

from pathlib import Path

from PyQt6.QtGui import QSurfaceFormat

from opencae.app.qt_opengl import opencae_surface_format
from opencae.app.qt_platform import is_wayland_session, recommended_qt_platform


ROOT = Path(__file__).resolve().parents[1]
_PYVISTA_VTK_97_COMMIT = "3ce36e3b72e5d73c10adf19256aeef6529579cc7"
_PYVISTAQT_WAYLAND_COMMIT = "c3fe1074dcb77bff723968b33a63181c08975f74"


def test_wayland_session_is_detected_from_session_type():
    """XDG_SESSION_TYPE=wayland must identify a native Wayland session."""
    assert is_wayland_session({"XDG_SESSION_TYPE": "wayland"})


def test_wayland_session_is_detected_from_display_socket():
    """WAYLAND_DISPLAY also identifies Wayland when session metadata is absent."""
    assert is_wayland_session({"WAYLAND_DISPLAY": "wayland-0"})


def test_linux_wayland_auto_mode_keeps_native_qt_selection():
    """Auto mode must no longer force a Wayland session through XWayland/xcb."""
    assert (
        recommended_qt_platform(
            system="Linux",
            environment={"XDG_SESSION_TYPE": "wayland"},
        )
        is None
    )


def test_explicit_qt_platform_is_never_overridden():
    """Standard Qt overrides must remain authoritative for users and CI."""
    assert (
        recommended_qt_platform(
            system="Linux",
            environment={
                "XDG_SESSION_TYPE": "wayland",
                "QT_QPA_PLATFORM": "offscreen",
            },
        )
        is None
    )


def test_explicit_opencae_xcb_fallback_remains_available():
    """Users with problematic drivers can still deliberately request XWayland."""
    assert (
        recommended_qt_platform(
            system="Linux",
            environment={
                "XDG_SESSION_TYPE": "wayland",
                "OPENCAE_QT_PLATFORM": "xcb",
            },
        )
        == "xcb"
    )


def test_explicit_wayland_override_remains_available():
    assert (
        recommended_qt_platform(
            system="Linux",
            environment={"OPENCAE_QT_PLATFORM": "wayland"},
        )
        == "wayland"
    )


def test_non_wayland_linux_keeps_qt_default():
    """X11 sessions also remain under Qt's native auto-selection."""
    assert (
        recommended_qt_platform(
            system="Linux",
            environment={"XDG_SESSION_TYPE": "x11"},
        )
        is None
    )


def test_qt_opengl_format_matches_qopenglwidget_vtk_bridge_requirements():
    fmt = opencae_surface_format()
    assert fmt.renderableType() == QSurfaceFormat.RenderableType.OpenGL
    assert fmt.profile() == QSurfaceFormat.OpenGLContextProfile.CoreProfile
    assert (fmt.majorVersion(), fmt.minorVersion()) == (3, 2)
    assert fmt.swapBehavior() == QSurfaceFormat.SwapBehavior.DoubleBuffer
    assert fmt.redBufferSize() == 8
    assert fmt.greenBufferSize() == 8
    assert fmt.blueBufferSize() == 8
    assert fmt.depthBufferSize() == 8
    assert fmt.alphaBufferSize() == 8
    assert fmt.stencilBufferSize() == 0
    assert fmt.samples() == 0


def test_qt_opengl_is_configured_before_qapplication_and_top_level_widgets():
    source = (ROOT / "opencae/app/application.py").read_text(encoding="utf-8")
    assert source.index("configure_qt_platform_environment()") < source.index(
        "from .qt_opengl import configure_qt_opengl"
    )
    assert source.index("configure_qt_opengl()") < source.index(
        "from PyQt6.QtWidgets import QApplication"
    )
    assert source.index("configure_qt_opengl()") < source.index("StartupWindow")


def test_vtk_stack_is_pinned_to_upstream_vtk97_wayland_bridge():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for dependency_file in (requirements, pyproject):
        assert _PYVISTA_VTK_97_COMMIT in dependency_file
        assert _PYVISTAQT_WAYLAND_COMMIT in dependency_file
        assert "vtk==9.7.0" in dependency_file
