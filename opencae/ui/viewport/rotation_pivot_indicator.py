"""Render a clear screen-space camera rotation pivot inside the VTK renderer."""

from __future__ import annotations

from PyQt6.QtGui import QColor
from vtkmodules.vtkFiltersSources import vtkRegularPolygonSource
from vtkmodules.vtkRenderingCore import vtkActor2D, vtkPolyDataMapper2D

from opencae.ui.core.theme import PALETTE


class RotationPivotIndicator:
    """Draw a simple high-contrast circle in VTK display coordinates."""

    RADIUS = 10.0

    def __init__(self, renderer):
        self._renderer = renderer
        self._source = vtkRegularPolygonSource()
        self._source.SetNumberOfSides(64)
        self._source.SetRadius(self.RADIUS)
        self._source.SetCenter(0.0, 0.0, 0.0)
        self._source.GeneratePolygonOff()

        mapper = vtkPolyDataMapper2D()
        mapper.SetInputConnection(self._source.GetOutputPort())

        self._outline = vtkActor2D()
        self._outline.SetMapper(mapper)
        self._outline.SetPickable(False)
        outline = QColor(PALETTE["panel_alt"])
        self._outline.GetProperty().SetColor(
            outline.redF(), outline.greenF(), outline.blueF()
        )
        self._outline.GetProperty().SetLineWidth(6.0)
        self._outline.SetVisibility(False)

        self._ring = vtkActor2D()
        self._ring.SetMapper(mapper)
        self._ring.SetPickable(False)
        accent = QColor(PALETTE["accent"])
        self._ring.GetProperty().SetColor(
            accent.redF(), accent.greenF(), accent.blueF()
        )
        self._ring.GetProperty().SetLineWidth(3.0)
        self._ring.SetVisibility(False)

        # PyVista's Renderer deliberately disables direct VTK PascalCase
        # methods. add_actor accepts vtkProp instances, including vtkActor2D,
        # while retaining PyVista's renderer bookkeeping.
        renderer.add_actor(self._outline, reset_camera=False, render=False)
        renderer.add_actor(self._ring, reset_camera=False, render=False)

    def set_center(self, x: float, y: float) -> None:
        """Place the circle center in VTK display-pixel coordinates."""
        self._source.SetCenter(float(x), float(y), 0.0)
        self._source.Modified()

    def show(self) -> None:
        self._outline.SetVisibility(True)
        self._ring.SetVisibility(True)

    def hide(self) -> None:
        self._outline.SetVisibility(False)
        self._ring.SetVisibility(False)

    def is_visible(self) -> bool:
        return bool(self._ring.GetVisibility())
