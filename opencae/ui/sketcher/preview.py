"""Isolated 3D preview surface for sketch-based geometry features."""

from __future__ import annotations

from copy import deepcopy

import pyvista as pv
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from opencae.geometry import GeometryService
from opencae.geometry.cache import CACHE
from opencae.model.entities.geometry import SketchFeatureMode
from opencae.model.entities.parts import Part, PartSourceKind
from opencae.ui.core.theme import PALETTE
from opencae.ui.viewport.safe_qt_interactor import SafeQtInteractor


def build_preview_part(base_part, feature) -> Part:
    """Return a fresh-identity Part representing the edited feature history.

    The live/detached source Part is never mutated and generated mesh payloads are
    intentionally not copied. Geometry settings and history are the only Part
    state the OCC rebuild needs for an exact feature preview.
    """
    if base_part is None:
        return Part(
            name="Sketch Preview",
            source_type=PartSourceKind.MANUAL,
            geometry=[deepcopy(feature)],
        )

    candidate = Part(
        name=f"{getattr(base_part, 'name', 'Part')} Preview",
        source_type=getattr(base_part, "source_type", PartSourceKind.MANUAL),
        metadata=deepcopy(getattr(base_part, "metadata", {})),
        geometry_settings=deepcopy(base_part.geometry_settings),
        geometry=deepcopy(base_part.geometry),
    )
    replacement = deepcopy(feature)
    for index, existing in enumerate(candidate.geometry):
        if existing.id == replacement.id:
            candidate.geometry[index] = replacement
            break
    else:
        candidate.geometry.append(replacement)
    return candidate


class SketchFeaturePreview(QWidget):
    """Build a detached Part and render the resulting authored OCC history."""

    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SketchFeaturePreview")
        self._base_part = None
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

    def set_part_context(self, part) -> None:
        """Set the Part whose complete feature history should be previewed."""
        self._base_part = part

    def refresh_feature(self, feature) -> bool:
        self.notice.hide()
        self.plotter.clear()
        candidate = build_preview_part(self._base_part, feature)
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
            if feature.mode is SketchFeatureMode.REVOLVE:
                bounds = snapshot.bounds
                if bounds:
                    extent = max(
                        abs(float(bounds[0])),
                        abs(float(bounds[1])),
                        abs(float(bounds[2])),
                        abs(float(bounds[3])),
                        abs(float(bounds[4])),
                        abs(float(bounds[5])),
                        1.0,
                    )
                else:
                    extent = 10.0
                line = pv.Line(
                    (-1.25 * extent, 0.0, 0.0),
                    (1.25 * extent, 0.0, 0.0),
                )
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
            # Preview candidates always have a fresh identity, so this cannot
            # invalidate the live Part's cached geometry.
            CACHE.invalidate(candidate.id)

    def refresh_theme(self):
        self.plotter.set_background(PALETTE["viewport"])
        self.plotter.render()


__all__ = ["SketchFeaturePreview", "build_preview_part"]
