from PyQt6.QtWidgets import QVBoxLayout, QWidget
from .meshability_legend import MeshabilityLegend
from .result_query_panel import ResultQueryPanel
from .result_selection_panel import ResultSelectionPanel
from .view_cube import ViewCube


class ViewportCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setObjectName("ViewportCanvas")
        self._layout = QVBoxLayout(self); self._layout.setContentsMargins(0,0,0,0); self._layout.setSpacing(0)
        self.cube = ViewCube(self); self.query = ResultQueryPanel(self); self.result_selection = ResultSelectionPanel(self)
        self.meshability = MeshabilityLegend(self)
        self.cube.hide(); self.query.hide(); self.result_selection.hide(); self.meshability.hide()
    def set_render_widget(self, widget):
        self._layout.addWidget(widget); self.cube.show(); self._position_overlays()
    def resizeEvent(self, event):
        super().resizeEvent(event); self._position_overlays()
    def _position_overlays(self):
        margin = 12; gap = 8
        self.cube.move(max(margin,self.width()-self.cube.width()-margin),margin)
        self.result_selection.move(margin, margin)
        query_y = margin + (self.result_selection.height() + gap if self.result_selection.isVisible() else 0)
        self.query.move(margin, query_y)
        self.meshability.move(
            max(margin, self.width() - self.meshability.width() - margin),
            max(margin, self.height() - self.meshability.height() - margin),
        )
        self.cube.raise_(); self.result_selection.raise_(); self.query.raise_(); self.meshability.raise_()
