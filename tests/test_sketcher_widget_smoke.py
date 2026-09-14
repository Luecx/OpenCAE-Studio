"""Runtime smoke coverage for the parametric Sketcher Qt surface."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


_SKETCH_DIALOG_SMOKE = r'''
from PyQt6.QtCore import Qt
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
    assert dialog.canvas.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert dialog.canvas.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff

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
        for action in dialog._constraint_actions.values()
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

    dimension_kinds = {
        str(action.property("dimensionKind"))
        for action in dialog._dimension_actions.values()
    }
    assert {
        "Distance",
        "DistanceX",
        "DistanceY",
        "Angle",
        "Radius",
        "Diameter",
    } <= dimension_kinds
    assert dialog.dimension_action.menu() is not None
    assert not dialog.dimension_action.icon().isNull()
    assert not dialog.grid_action.icon().isNull()
    assert not dialog.construction_action.icon().isNull()

    # The narrow state must become exactly the three semantic group buttons.
    assert dialog.ribbon._target_collapsed_groups(700) == frozenset(
        {"PRIMITIVES", "CONSTRAINTS", "CONSTRUCTION/GRID"}
    )

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
    IconKind.SKETCH_ARC_CENTER,
    IconKind.SKETCH_ARC_3POINT,
    IconKind.SKETCH_ELLIPSE,
    IconKind.SKETCH_SPLINE,
    IconKind.SKETCH_SLOT,
    IconKind.SKETCH_PRIMITIVES_MORE,
    IconKind.SKETCH_CONSTRUCTION,
    IconKind.SKETCH_GRID,
    IconKind.SKETCH_SNAP,
    IconKind.SKETCH_CONSTRAINT,
    IconKind.SKETCH_CONSTRAINT_COINCIDENT,
    IconKind.SKETCH_CONSTRAINT_HORIZONTAL,
    IconKind.SKETCH_CONSTRAINT_VERTICAL,
    IconKind.SKETCH_CONSTRAINT_PARALLEL,
    IconKind.SKETCH_CONSTRAINT_PERPENDICULAR,
    IconKind.SKETCH_CONSTRAINT_TANGENT,
    IconKind.SKETCH_CONSTRAINT_EQUAL,
    IconKind.SKETCH_CONSTRAINT_CONCENTRIC,
    IconKind.SKETCH_CONSTRAINT_MIDPOINT,
    IconKind.SKETCH_CONSTRAINT_COLLINEAR,
    IconKind.SKETCH_CONSTRAINT_POINT_ON,
    IconKind.SKETCH_CONSTRAINT_SYMMETRY,
    IconKind.SKETCH_CONSTRAINT_FIXED,
    IconKind.SKETCH_CONSTRAINT_MORE,
    IconKind.SKETCH_DIMENSION,
    IconKind.SKETCH_DIMENSION_DISTANCE,
    IconKind.SKETCH_DIMENSION_HORIZONTAL,
    IconKind.SKETCH_DIMENSION_VERTICAL,
    IconKind.SKETCH_DIMENSION_ANGLE,
    IconKind.SKETCH_DIMENSION_RADIUS,
    IconKind.SKETCH_DIMENSION_DIAMETER,
)
assert all(not make_icon(kind, 42).isNull() for kind in kinds)
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


def test_sketch_dialog_constructs_with_responsive_ribbon_and_mode_switch():
    _run_isolated_qt(_SKETCH_DIALOG_SMOKE)


def test_all_semantic_sketch_icons_render_through_shared_factory():
    _run_isolated_qt(_SKETCH_ICON_SMOKE)
