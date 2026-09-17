"""Isolated 3D preview surface for sketch-based geometry features."""

from __future__ import annotations

from copy import deepcopy
import logging

import pyvista as pv
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from opencae.geometry import GeometryService
from opencae.geometry.cache import CACHE
from opencae.model.entities.geometry import SketchFeatureMode
from opencae.model.entities.parts import Part, PartSourceKind
from opencae.ui.foundation.theme import PALETTE
from opencae.ui.other.viewport.safe_qt_interactor import SafeQtInteractor


_LOG = logging.getLogger(__name__)


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
        self._closed = False
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.notice = QLabel("")
        self.notice.setObjectName("SketchPreviewNotice")
        self.notice.setWordWrap(True)
        self.notice.hide()
        self._layout.addWidget(self.notice)

        # Do not create a native VTK/OpenGL child until the user actually opens
        # 3D Preview. Hidden QVTK children can still acquire native HWND/WGL
        # resources on Windows and may interfere with sibling QWidget stacking
        # before the preview page is ever shown. The normal Sketch page is now
        # pure Qt and follows exactly the same toolbar/layout path as the main
        # viewport until 3D Preview is requested.
        self.plotter = None

        # QDialog closes its native parent window before Python necessarily
        # destroys all child wrappers. On Windows that can leave VTK trying to
        # make a WGL context current on an HWND that is already invalid. Finalize
        # this child render window while the dialog still owns a valid native
        # window instead of relying on QObject destruction order.
        finished = getattr(parent, "finished", None)
        if finished is not None and hasattr(finished, "connect"):
            finished.connect(self._parent_dialog_finished)

    def _ensure_plotter(self):
        """Create the native render surface only when 3D preview is requested."""
        if self._closed:
            return None
        if self.plotter is None:
            self.plotter = SafeQtInteractor(self)
            self._layout.addWidget(self.plotter, 1)
            self.plotter.set_background(PALETTE["viewport"])
        return self.plotter

    def _parent_dialog_finished(self, _result=None) -> None:
        self.shutdown()

    def shutdown(self) -> None:
        """Idempotently release the preview render window before Qt teardown."""
        if self._closed:
            return
        self._closed = True
        plotter = self.plotter
        if plotter is None:
            return
        try:
            plotter.close()
        except (AttributeError, RuntimeError) as exc:
            # Teardown must never keep a dialog alive just because the platform
            # already disposed the native render surface. Log at debug level so
            # an actual lifecycle regression remains diagnosable.
            _LOG.debug("Sketch preview render window was already closed: %s", exc)

    def closeEvent(self, event):
        self.shutdown()
        super().closeEvent(event)

    def set_part_context(self, part) -> None:
        """Set the Part whose complete feature history should be previewed."""
        self._base_part = part

    def refresh_feature(self, feature) -> bool:
        if self._closed:
            return False
        plotter = self._ensure_plotter()
        if plotter is None:
            return False
        self.notice.hide()
        plotter.clear()
        candidate = build_preview_part(self._base_part, feature)
        try:
            snapshot = GeometryService().build_geometry(candidate, force=True)
            for patch in snapshot.surfaces:
                if not len(patch.points) or not len(patch.faces):
                    continue
                mesh = pv.PolyData(patch.points, patch.faces)
                plotter.add_mesh(
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
                    plotter.add_mesh(
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
                plotter.add_mesh(
                    line,
                    color=PALETTE["axis_x"],
                    line_width=2.0,
                    pickable=False,
                )
            plotter.camera_position = "iso"
            self.fit_view()
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

    def fit_view(self) -> None:
        """Fit the current preview using the same compact viewport-bar affordance."""
        if self._closed or self.plotter is None:
            return
        self.plotter.reset_camera()
        self.plotter.render()

    def refresh_theme(self):
        if self._closed or self.plotter is None:
            return
        self.plotter.set_background(PALETTE["viewport"])
        self.plotter.render()


__all__ = ["SketchFeaturePreview", "build_preview_part"]
