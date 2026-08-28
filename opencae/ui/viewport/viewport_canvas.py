"""Host the VTK render widget and lightweight Qt viewport overlays."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QWidget

from opencae.ui.core.theme import PALETTE
from .meshability_legend import MeshabilityLegend
from .result_query_panel import ResultQueryPanel
from .result_selection_panel import ResultSelectionPanel
from .view_cube import ViewCube
from .viewport_notice import ViewportNotice
from .viewport_overlay_metrics import (
    VIEWPORT_OVERLAY_GAP,
    VIEWPORT_OVERLAY_MARGIN,
)


class ViewportCanvas(QWidget):
    """Own the render surface plus independently positioned viewport overlays."""

    def __init__(self, parent=None):
        """Create hidden overlays before the render widget is attached."""
        super().__init__(parent)
        self.setObjectName("ViewportCanvas")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._render_widget = None
        self.cube = None
        self.horizon = None
        self.query = ResultQueryPanel(self)
        self.result_selection = ResultSelectionPanel(self)
        self.meshability = MeshabilityLegend(self)
        self.notice = ViewportNotice(self)
        self.query.hide()
        self.result_selection.hide()
        self.meshability.hide()
        self.notice.hide()

    def set_render_widget(self, widget):
        """Attach the VTK surface and construct overlays with their final parent."""
        self._render_widget = widget
        self._layout.addWidget(widget)
        # QVTK is a native child. Keep the lightweight horizon and ViewCube as
        # children of that native surface so they compose reliably on X11 and
        # Wayland/XWayland instead of depending on sibling-window stacking.
        self.horizon = QFrame(widget)
        self.horizon.setObjectName("ViewportHorizon")
        self.horizon.setFixedHeight(1)
        self.horizon.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        self.horizon.setStyleSheet(
            f"QFrame#ViewportHorizon {{ background: {PALETTE['viewport_horizon']}; border: none; }}"
        )
        self.horizon.show()

        # Reparenting an existing QWidget onto QVTK's native child can produce
        # BadWindow failures on X11/offscreen backends.
        self.cube = ViewCube(widget)
        self.cube.show()
        self._position_overlays()

    def resizeEvent(self, event):
        """Keep all overlays anchored when the viewport is resized."""
        super().resizeEvent(event)
        self._position_overlays()

    def _position_overlays(self):
        """Position corner overlays, horizon, and centered workflow guidance."""
        margin = VIEWPORT_OVERLAY_MARGIN
        gap = VIEWPORT_OVERLAY_GAP
        if self.horizon is not None and self._render_widget is not None:
            render_width = max(0, self._render_widget.width())
            render_height = max(0, self._render_widget.height())
            self.horizon.setGeometry(
                0,
                round(render_height * 0.62),
                render_width,
                1,
            )
            self.horizon.raise_()
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
        self.notice.move(
            max(margin, (self.width() - self.notice.width()) // 2),
            max(margin, (self.height() - self.notice.height()) // 2),
        )
        if self.cube is not None:
            self.cube.raise_()
        self.result_selection.raise_()
        self.query.raise_()
        self.meshability.raise_()
        self.notice.raise_()
