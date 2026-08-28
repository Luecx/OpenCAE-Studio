"""Native Wayland smoke coverage for the Qt-owned PyVistaQt OpenGL bridge."""

from __future__ import annotations

import os

import pytest


def test_native_wayland_uses_qopenglwidget_generic_vtk_render_window():
    """Exercise one real OpenCAE viewport widget on a native Wayland compositor."""
    if os.environ.get("OPENCAE_WAYLAND_SMOKE") != "1":
        pytest.skip("Wayland compositor smoke test runs in its dedicated CI job")

    # Do exactly what application.py does before QApplication exists.
    from opencae.app.qt_platform import configure_qt_platform_environment

    assert configure_qt_platform_environment() is None

    from opencae.app.qt_opengl import configure_qt_opengl

    configure_qt_opengl()

    from PyQt6.QtGui import QGuiApplication
    from PyQt6.QtWidgets import QApplication
    import pyvista as pv

    app = QApplication.instance() or QApplication([])
    assert QGuiApplication.platformName().startswith("wayland")

    from opencae.ui.viewport.safe_qt_interactor import SafeQtInteractor

    viewport = SafeQtInteractor()
    try:
        viewport.resize(360, 260)
        viewport.add_mesh(pv.Sphere(theta_resolution=12, phi_resolution=12))
        viewport.show()
        # Realize QOpenGLWidget and let the Qt-owned framebuffer render at least
        # once. No native window id is passed to VTK on this architecture.
        for _ in range(4):
            app.processEvents()
        viewport.render()
        for _ in range(4):
            app.processEvents()

        render_window = viewport.GetRenderWindow()
        assert render_window.GetClassName() == "vtkGenericOpenGLRenderWindow"
        assert viewport.isVisible()
    finally:
        viewport.close()
        app.processEvents()
