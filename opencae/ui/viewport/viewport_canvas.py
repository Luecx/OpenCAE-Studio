"""Host the VTK render widget and position persistent viewport overlays."""

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from .meshability_legend import MeshabilityLegend
from .result_query_panel import ResultQueryPanel
from .result_selection_panel import ResultSelectionPanel
from .view_cube import ViewCube


class ViewportCanvas(QWidget):
    """Own the render surface container and its independently positioned overlays."""

    def __init__(self, parent=None):
        """Create hidden overlays that become visible with a render widget."""
        super().__init__(parent)
        self.setObjectName("ViewportCanvas")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.cube = None
        self.query = ResultQueryPanel(self)
        self.result_selection = ResultSelectionPanel(self)
        self.meshability = MeshabilityLegend(self)
        self.query.hide()
        self.result_selection.hide()
        self.meshability.hide()

    def set_render_widget(self, widget):
        """Install the render surface and anchor the opaque cube directly above it."""
        self._layout.addWidget(widget)
        # Construct with the final parent. Reparenting a QWidget onto QVTK's
        # native child can produce BadWindow failures on X11/offscreen backends.
        self.cube = ViewCube(widget)
        self.cube.show()
        self._position_overlays()

    def resizeEvent(self, event):
        """Re-anchor overlays whenever the render canvas changes size."""
        super().resizeEvent(event)
        self._position_overlays()

    def _position_overlays(self):
        """Place all overlay widgets against their designated viewport corners."""
        margin = 12
        gap = 8
        if self.cube is not None:
            self.cube.move(
                max(margin, self.width() - self.cube.width() - margin),
                margin,
            )
        self.result_selection.move(margin, margin)
        query_y = margin + (
            self.result_selection.height() + gap
            if self.result_selection.isVisible()
            else 0
        )
        self.query.move(margin, query_y)
        self.meshability.move(
            max(margin, self.width() - self.meshability.width() - margin),
            max(margin, self.height() - self.meshability.height() - margin),
        )
        if self.cube is not None:
            self.cube.raise_()
        self.result_selection.raise_()
        self.query.raise_()
        self.meshability.raise_()
