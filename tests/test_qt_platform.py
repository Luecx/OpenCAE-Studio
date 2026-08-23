"""Tests OpenCAE's pre-QApplication Qt platform selection policy."""

from opencae.app.qt_platform import is_wayland_session, recommended_qt_platform


def test_wayland_session_is_detected_from_session_type():
    """XDG_SESSION_TYPE=wayland must identify a native Wayland session."""
    assert is_wayland_session({"XDG_SESSION_TYPE": "wayland"})


def test_wayland_session_is_detected_from_display_socket():
    """WAYLAND_DISPLAY also identifies Wayland when session metadata is absent."""
    assert is_wayland_session({"WAYLAND_DISPLAY": "wayland-0"})


def test_linux_wayland_defaults_to_xcb_for_current_vtk_bridge():
    """Auto mode must keep Qt and the current X11 VTK bridge on one backend."""
    assert (
        recommended_qt_platform(
            system="Linux",
            environment={"XDG_SESSION_TYPE": "wayland"},
        )
        == "xcb"
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


def test_native_override_allows_wayland_development():
    """Developers must be able to opt into the future native Wayland path."""
    assert (
        recommended_qt_platform(
            system="Linux",
            environment={
                "XDG_SESSION_TYPE": "wayland",
                "OPENCAE_QT_PLATFORM": "native",
            },
        )
        is None
    )


def test_non_wayland_linux_keeps_qt_default():
    """X11 sessions do not need an OpenCAE-specific QPA override."""
    assert (
        recommended_qt_platform(
            system="Linux",
            environment={"XDG_SESSION_TYPE": "x11"},
        )
        is None
    )
