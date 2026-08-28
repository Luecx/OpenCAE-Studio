"""Configure the process-wide Qt OpenGL surface used by PyVistaQt/VTK."""

from __future__ import annotations

from PyQt6.QtGui import QSurfaceFormat


def opencae_surface_format() -> QSurfaceFormat:
    """Return the desktop OpenGL format required by the QOpenGLWidget VTK bridge."""
    fmt = QSurfaceFormat()
    fmt.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    fmt.setVersion(3, 2)
    fmt.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
    fmt.setRedBufferSize(8)
    fmt.setGreenBufferSize(8)
    fmt.setBlueBufferSize(8)
    fmt.setDepthBufferSize(8)
    fmt.setAlphaBufferSize(8)
    fmt.setStencilBufferSize(0)
    # VTK performs multisampling in its own framebuffer objects. Requesting Qt
    # MSAA here can make the top-level share context incompatible on Wayland.
    fmt.setSamples(0)
    return fmt


def configure_qt_opengl() -> QSurfaceFormat:
    """Install OpenCAE's GL format before QApplication/top-level widgets exist."""
    fmt = opencae_surface_format()
    QSurfaceFormat.setDefaultFormat(fmt)
    return fmt
