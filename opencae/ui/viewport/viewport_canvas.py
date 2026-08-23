"""Hosts the render widget and lightweight Qt overlays around the 3D viewport."""

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from .meshability_legend import MeshabilityLegend
from .result_query_panel import ResultQueryPanel
from .result_selection_panel import ResultSelectionPanel
from .view_cube import ViewCube
from .viewport_notice import ViewportNotice


class ViewportCanvas(QWidget):
    """Own the render surface plus positioned non-VTK viewport overlays."""

    def __init__(self, parent=None):
        """Create viewport overlays before the render widget is attached."""
        super().__init__(parent)
        self.setObjectName("ViewportCanvas")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.cube = ViewCube(self)
        self.query = ResultQueryPanel(self)
        self.result_selection = ResultSelectionPanel(self)
        self.meshability = MeshabilityLegend(self)
        self.notice = ViewportNotice(self)
        self.cube.hide()
        self.query.hide()
        self.result_selection.hide()
        self.meshability.hide()
        self.notice.hide()

    def set_render_widget(self, widget):
        """Attach the VTK render widget and position all overlays."""
        self._layout.addWidget(widget)
        self.cube.show()
        self._position_overlays()

    def resizeEvent(self, event):
        """Keep overlays anchored when the viewport is resized."""
        super().resizeEvent(event)
        self._position_overlays()

    def _position_overlays(self):
        """Position corner overlays and center the workflow guidance notice."""
        margin = 12
        gap = 8
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
        self.notice.move(
            max(margin, (self.width() - self.notice.width()) // 2),
            max(margin, (self.height() - self.notice.height()) // 2),
        )
        self.cube.raise_()
        self.result_selection.raise_()
        self.query.raise_()
        self.meshability.raise_()
        self.notice.raise_()
