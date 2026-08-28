"""Regression coverage for viewport overlays and ribbon vertical geometry."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import QAction, QIcon, QPixmap
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QWidget

from opencae.ui.core.metrics import RIBBON_BUTTON_HEIGHT
from opencae.ui.templates import action_button
from opencae.ui.viewport.result_query_model import QueryResult
from opencae.ui.viewport.result_query_panel import ResultQueryPanel
from opencae.ui.viewport.scalar_bar import _cap_rectangles, scalar_bar_args
from opencae.ui.viewport.view_cube import ViewCube
from opencae.ui.viewport.viewport_overlay_metrics import (
    VIEW_CUBE_SIZE,
    VIEWPORT_OVERLAY_GAP,
    VIEWPORT_OVERLAY_MARGIN,
)

_QT_APPLICATION: QApplication | None = None


def _application() -> QApplication:
    """Return the shared Qt application used by offscreen geometry tests."""
    global _QT_APPLICATION
    _QT_APPLICATION = QApplication.instance() or QApplication([])
    return _QT_APPLICATION


class _MouseCounter(QObject):
    """Count propagated mouse presses/releases received by a parent widget."""

    def __init__(self):
        super().__init__()
        self.events = []

    def eventFilter(self, watched, event):
        del watched
        if event.type() in {
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonRelease,
        }:
            self.events.append(event.type())
        return False


def test_view_cube_click_does_not_propagate_to_render_parent():
    """Cube clicks must not leave the underlying VTK interactor rotating."""
    app = _application()
    parent = QWidget()
    parent.resize(320, 240)
    cube = ViewCube(parent)
    counter = _MouseCounter()
    parent.installEventFilter(counter)
    parent.show()
    cube.show()
    app.processEvents()

    QTest.mouseClick(
        cube,
        Qt.MouseButton.LeftButton,
        pos=cube.rect().center(),
    )
    app.processEvents()

    assert cube.testAttribute(Qt.WidgetAttribute.WA_NoMousePropagation)
    assert counter.events == []


class _Plotter:
    """Expose a deterministic viewport height to scalar-bar layout code."""

    def __init__(self, height):
        self._height = height

    def height(self):
        return self._height


def test_scalar_bar_reserves_cube_space_and_disables_native_range_swatches():
    """The main bar stays below the cube while OpenCAE owns outside end caps."""
    viewport_height = 600
    args = scalar_bar_args(
        "STRESS:SXX",
        _Plotter(viewport_height),
        outside_colors=True,
    )
    cube_bottom = 1.0 - (
        VIEWPORT_OVERLAY_MARGIN + VIEW_CUBE_SIZE + VIEWPORT_OVERLAY_GAP
    ) / viewport_height

    assert args["position_y"] + args["height"] <= cube_bottom + 1.0e-9
    assert args["title_font_size"] >= 13
    assert args["label_font_size"] >= 11
    assert args["width"] <= 0.05
    # Explicit None prevents PyVista from enabling VTK's thick, padded built-in
    # above/below swatches. OpenCAE supplies its own compact colored caps.
    assert args["below_label"] is None
    assert args["above_label"] is None

    no_caps = scalar_bar_args("STRESS:SXX", _Plotter(viewport_height))
    assert "below_label" not in no_caps
    assert "above_label" not in no_caps


def test_scalar_bar_custom_caps_are_thin_and_exactly_touch_main_bar():
    """Outside-range caps have independent thickness and zero pixel gap."""
    bar = (50, 100, 18, 320)
    below, above = _cap_rectangles(bar, cap_pixels=6)

    assert below == (50, 94, 18, 6)
    assert above == (50, 420, 18, 6)
    assert below[1] + below[3] == bar[1]
    assert above[1] == bar[1] + bar[3]
    assert below[3] == above[3] == 6
    assert below[3] < bar[2]


def test_result_query_panel_caps_matrix_to_available_viewport_height():
    """Large element-query matrices stay inside the canvas instead of clipping."""
    app = _application()
    parent = QWidget()
    parent.resize(500, 360)
    panel = ResultQueryPanel(parent)
    panel.move(12, 90)
    parent.show()
    panel.show_result(
        "Element Query — Stress / Magnitude",
        QueryResult(
            summary=[
                ("Element", 42),
                ("Cell type", "Quadratic Hexahedron"),
                ("Component", "Magnitude"),
            ],
            columns=["Node", "Magnitude"],
            matrix=[[index, f"{index * 1.234567:.7g}"] for index in range(1, 21)],
        ),
    )
    app.processEvents()
    panel._fit_to_contents()

    assert panel.y() + panel.height() <= parent.height() - VIEWPORT_OVERLAY_MARGIN
    assert panel.table.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded


def test_two_line_ribbon_caption_fits_canonical_button_height():
    """Two-line action captions fit inside the shared ribbon-button geometry."""
    app = _application()
    action = QAction("Add Instance")
    pixmap = QPixmap(42, 42)
    pixmap.fill(Qt.GlobalColor.transparent)
    action.setIcon(QIcon(pixmap))
    button = action_button(action)
    button.show()
    app.processEvents()

    assert RIBBON_BUTTON_HEIGHT >= 80
    assert "\n" in button.text()
    assert button.height() >= button.sizeHint().height()
