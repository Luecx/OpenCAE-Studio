"""Runtime smoke coverage for the parametric Sketcher Qt surface."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


_SKETCH_DIALOG_SMOKE = r'''
from PyQt6.QtWidgets import QApplication, QWidget

import opencae.ui.sketcher.dialog as dialog_module
from opencae.model.entities.geometry import SketchFeature


class PreviewStub(QWidget):
    def set_part_context(self, _part):
        return None

    def refresh_feature(self, _feature):
        return True

    def refresh_theme(self):
        return None


dialog_module.SketchFeaturePreview = PreviewStub

from opencae.ui.sketcher import SketchFeatureDialog

app = QApplication.instance() or QApplication([])
dialog = SketchFeatureDialog(
    SketchFeature(name="Runtime Sketch", mode="Extrusion", depth=5.0)
)
try:
    assert dialog.canvas.tool == "Select"
    assert dialog.mode_combo.currentText() == "Extrusion"
    assert not dialog.canvas.show_revolve_axis

    for tool in (
        "Select",
        "Point",
        "Line",
        "Polyline",
        "Rectangle",
        "Circle",
        "Center Arc",
        "3-Point Arc",
        "Ellipse",
        "Spline",
        "Slot",
    ):
        action = dialog._tool_actions[tool]
        assert not action.icon().isNull(), tool

    constraint_kinds = {
        str(action.property("constraintKind"))
        for action in dialog.toolbar.actions()
        if action.property("constraintKind")
    }
    assert {
        "Coincident",
        "Horizontal",
        "Vertical",
        "Parallel",
        "Perpendicular",
        "Tangent",
        "Equal",
        "Concentric",
        "Midpoint",
        "Collinear",
        "Point on object",
        "Symmetry",
        "Fixed",
    } <= constraint_kinds

    dialog.mode_combo.setCurrentText("Revolve")
    assert dialog.canvas.show_revolve_axis
    assert dialog.depth_spin.isHidden()
    assert not dialog.angle_spin.isHidden()
finally:
    dialog.close()
    app.processEvents()
'''


_SKETCH_ICON_SMOKE = r'''
from PyQt6.QtWidgets import QApplication

from opencae.ui.core.icon_factory import IconKind, make_icon

app = QApplication.instance() or QApplication([])
kinds = (
    IconKind.SKETCH_SELECT,
    IconKind.SKETCH_POINT,
    IconKind.SKETCH_LINE,
    IconKind.SKETCH_POLYLINE,
    IconKind.SKETCH_RECTANGLE,
    IconKind.SKETCH_CIRCLE,
    IconKind.SKETCH_ARC,
    IconKind.SKETCH_ELLIPSE,
    IconKind.SKETCH_SPLINE,
    IconKind.SKETCH_SLOT,
    IconKind.SKETCH_CONSTRUCTION,
    IconKind.SKETCH_CONSTRAINT,
    IconKind.SKETCH_DIMENSION,
)
assert all(not make_icon(kind, 24).isNull() for kind in kinds)
'''


def _run_isolated_qt(script: str) -> None:
    """Run one Qt smoke probe without inheriting native VTK/Qt process state."""

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


def test_sketch_dialog_constructs_with_complete_toolbar_and_mode_switch():
    _run_isolated_qt(_SKETCH_DIALOG_SMOKE)


def test_all_semantic_sketch_icons_render_through_shared_factory():
    _run_isolated_qt(_SKETCH_ICON_SMOKE)
