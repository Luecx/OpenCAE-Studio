"""Regression coverage for viewport overlays and ribbon vertical geometry."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from vtkmodules.vtkRenderingAnnotation import vtkScalarBarActor

from opencae.ui.other.viewport.scalar_bar import (
    _cap_rectangles,
    _disable_native_range_swatches,
    scalar_bar_args,
)
from opencae.ui.other.viewport.viewport_overlay_metrics import (
    VIEW_CUBE_SIZE,
    VIEWPORT_OVERLAY_GAP,
    VIEWPORT_OVERLAY_MARGIN,
)


ROOT = Path(__file__).resolve().parents[1]


def _run_isolated_qt(script: str) -> None:
    """Run one real Qt/VTK interaction probe in a fresh native lifecycle."""
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["PYVISTA_OFF_SCREEN"] = "true"
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout


def test_view_cube_click_does_not_propagate_to_render_parent():
    """Cube clicks must not leave the underlying VTK interactor rotating."""
    _run_isolated_qt(r'''
from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QWidget
from opencae.ui.other.viewport.view_cube import ViewCube

class MouseCounter(QObject):
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

app = QApplication.instance() or QApplication([])
parent = QWidget()
parent.resize(320, 240)
cube = ViewCube(parent)
counter = MouseCounter()
parent.installEventFilter(counter)
try:
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
finally:
    parent.close()
    parent.deleteLater()
    app.processEvents()
''')


class _Plotter:
    """Expose a deterministic viewport height to scalar-bar layout code."""

    def __init__(self, height):
        self._height = height

    def height(self):
        return self._height


def test_scalar_bar_reserves_cube_space_without_native_range_labels():
    """The main bar stays below the cube and does not request swatch labels."""
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
    assert "below_label" not in args
    assert "above_label" not in args


def test_scalar_bar_native_range_swatches_are_explicitly_disabled():
    """PyVista's LUT colors must not resurrect VTK's thick padded swatches."""
    actor = vtkScalarBarActor()
    actor.DrawBelowRangeSwatchOn()
    actor.DrawAboveRangeSwatchOn()
    assert actor.GetDrawBelowRangeSwatch()
    assert actor.GetDrawAboveRangeSwatch()

    _disable_native_range_swatches(actor)

    assert not actor.GetDrawBelowRangeSwatch()
    assert not actor.GetDrawAboveRangeSwatch()


def test_scalar_bar_custom_caps_use_configured_outside_colors():
    """The cap actors must use exactly the colors selected in the contour menu."""
    _run_isolated_qt(r'''
import numpy as np
import pyvista as pv
from opencae.ui.other.viewport.scalar_bar import install_scalar_bar_end_caps, scalar_bar_args

plotter = pv.Plotter(off_screen=True, window_size=(360, 360))
mesh = pv.Sphere(theta_resolution=8, phi_resolution=8)
mesh["value"] = np.asarray(mesh.points)[:, 2]
try:
    plotter.add_mesh(
        mesh,
        scalars="value",
        clim=(-0.5, 0.5),
        below_color="#345678",
        above_color="#c08040",
        scalar_bar_args=scalar_bar_args(
            "value",
            plotter,
            outside_colors=True,
        ),
        render=False,
    )
    state = install_scalar_bar_end_caps(
        plotter,
        "value",
        below_color="#345678",
        above_color="#c08040",
    )
    assert state is not None
    scalar_actor = plotter.scalar_bars["value"]
    assert not scalar_actor.GetDrawBelowRangeSwatch()
    assert not scalar_actor.GetDrawAboveRangeSwatch()
    assert np.allclose(
        state["below_actor"].GetProperty().GetColor(),
        (0x34 / 255.0, 0x56 / 255.0, 0x78 / 255.0),
    )
    assert np.allclose(
        state["above_actor"].GetProperty().GetColor(),
        (0xC0 / 255.0, 0x80 / 255.0, 0x40 / 255.0),
    )
finally:
    plotter.close()
''')


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
    _run_isolated_qt(r'''
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QWidget
from opencae.ui.other.viewport.result_query_model import QueryResult
from opencae.ui.other.viewport.result_query_panel import ResultQueryPanel
from opencae.ui.other.viewport.viewport_overlay_metrics import VIEWPORT_OVERLAY_MARGIN

app = QApplication.instance() or QApplication([])
parent = QWidget()
parent.resize(500, 360)
panel = ResultQueryPanel(parent)
try:
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
finally:
    parent.close()
    parent.deleteLater()
    app.processEvents()
''')


def test_two_line_ribbon_caption_fits_canonical_button_height():
    """Two-line action captions fit inside the shared ribbon-button geometry."""
    _run_isolated_qt(r'''
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon, QPixmap
from PyQt6.QtWidgets import QApplication
from opencae.ui.foundation.metrics import RIBBON_BUTTON_HEIGHT
from opencae.ui.primitives.buttons import ribbon_button_for_action

app = QApplication.instance() or QApplication([])
action = QAction("Add Instance")
pixmap = QPixmap(42, 42)
pixmap.fill(Qt.GlobalColor.transparent)
action.setIcon(QIcon(pixmap))
button = ribbon_button_for_action(action)
try:
    button.show()
    app.processEvents()
    assert RIBBON_BUTTON_HEIGHT >= 80
    assert "\n" in button.text()
    assert button.height() >= button.sizeHint().height()
finally:
    button.close()
    button.deleteLater()
    app.processEvents()
''')
