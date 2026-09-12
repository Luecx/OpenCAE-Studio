"""Isolated 3D preview surface for sketch-based geometry features."""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pyvista as pv
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from opencae.geometry import GeometryService
from opencae.geometry.cache import CACHE
from opencae.model.entities.parts import Part, PartSourceKind
from opencae.ui.core.theme import PALETTE
from opencae.ui.viewport.safe_qt_interactor import SafeQtInteractor


class SketchFeaturePreview(QWidget):
    """Build a detached Part and render its authored OCC result."""

    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SketchFeaturePreview")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.notice = QLabel("")
        self.notice.setObjectName("SketchPreviewNotice")
        self.notice.setWordWrap(True)
        self.notice.hide()
        layout.addWidget(self.notice)
        self.plotter = SafeQtInteractor(self)
        layout.addWidget(self.plotter, 1)
        self.plotter.set_background(PALETTE["viewport"])

    def refresh_feature(self, feature) -> bool:
        self.notice.hide()
        self.plotter.clear()
        candidate = Part(
            name="Sketch Preview",
            source_type=PartSourceKind.MANUAL,
            geometry=[deepcopy(feature)],
        )
        try:
            snapshot = GeometryService().build_geometry(candidate, force=True)
            for patch in snapshot.surfaces:
                if not len(patch.points) or not len(patch.faces):
                    continue
                mesh = pv.PolyData(patch.points, patch.faces)
                self.plotter.add_mesh(
                    mesh,
                    color=PALETTE["cad_face"],
                    edge_color=PALETTE["cad_edge"],
                    show_edges=True,
                    smooth_shading=False,
                    opacity=0.92,
                    pickable=False,
                )
            for patch in snapshot.edges:
                if len(patch.points) < 2:
                    continue
                try:
                    mesh = pv.PolyData(patch.points, lines=patch.lines)
                    self.plotter.add_mesh(
                        mesh,
                        color=PALETTE["cad_edge"],
                        line_width=1.4,
                        pickable=False,
                    )
                except (TypeError, ValueError):
                    continue
            if str(getattr(feature, "mode", "")).casefold() == "revolve":
                bounds = snapshot.bounds
                if bounds:
                    extent = max(
                        abs(float(bounds[0])), abs(float(bounds[1])),
                        abs(float(bounds[2])), abs(float(bounds[3])),
                        abs(float(bounds[4])), abs(float(bounds[5])), 1.0,
                    )
                else:
                    extent = 10.0
                line = pv.Line((-1.25 * extent, 0.0, 0.0), (1.25 * extent, 0.0, 0.0))
                self.plotter.add_mesh(
                    line,
                    color=PALETTE["axis_x"],
                    line_width=2.0,
                    pickable=False,
                )
            self.plotter.camera_position = "iso"
            self.plotter.reset_camera()
            self.plotter.render()
            return True
        except Exception as exc:
            message = str(exc)
            self.notice.setText(f"Preview unavailable: {message}")
            self.notice.show()
            self.error.emit(message)
            return False
        finally:
            CACHE.invalidate(candidate.id)

    def refresh_theme(self):
        self.plotter.set_background(PALETTE["viewport"])
        self.plotter.render()
