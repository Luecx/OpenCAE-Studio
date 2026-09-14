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

    def fit_view(self):
        return None


dialog_module.SketchFeaturePreview = PreviewStub

from opencae.ui.sketcher import SketchFeatureDialog

app = QApplication.instance() or QApplication([])
dialog = SketchFeatureDialog(
    SketchFeature(name="Runtime Sketch", mode="Extrusion", depth=5.0)
)
try:
    # Layout regressions only show up after Qt has actually polished and shown
    # the widgets.  Construction-time parent checks are not enough: a toolbar
    # can exist while being compressed to zero pixels by a splitter/layout.
    dialog.show()
    app.processEvents()

    assert dialog.canvas.tool == "Select"
    assert dialog.mode_combo.currentText() == "Extrusion"
    assert not dialog.canvas.show_revolve_axis
    assert dialog.canvas.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert dialog.canvas.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert dialog.canvas.frameShape().name == "NoFrame"

    # The slim command bar is a real visible strip between the ribbon and the
    # drafting stack.  It must never be collapsed or covered by the canvas.
    bar = dialog.viewport_toolbar
    host = bar.parentWidget()
    assert bar.objectName() == "ViewportToolbar"
    assert bar.isVisibleTo(dialog)
    assert bar.height() >= 38
    assert bar.width() > 200
    assert bar.geometry().top() == 0
    assert dialog.workspace.geometry().top() >= bar.geometry().bottom() + 1
    assert dialog.workspace.height() > 100
    assert dialog.view_sketch.isVisibleTo(dialog)
    assert dialog.view_preview.isVisibleTo(dialog)
    assert dialog.fit_button.isVisibleTo(dialog)
    assert dialog.status_label.isVisibleTo(dialog)
    assert dialog.buttons.isVisibleTo(dialog)
    assert host.height() >= bar.height() + dialog.workspace.minimumSizeHint().height()

    footer = dialog.findChild(QWidget, "SketchLegacyFooter")
    assert footer is not None
    assert footer.isHidden()
    assert footer.width() == 0
    assert footer.height() == 0

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

    titles = tuple(spec.title for spec in dialog.ribbon._specs)
    assert titles == (
        "SELECTION",
        "PRIMITIVES",
        "CONSTRAINTS",
        "DIMENSIONS",
        "CONSTRUCTION/GRID",
    )
    expanded_width = dialog.ribbon._required_width(frozenset()) + 20
    assert dialog.ribbon._target_collapsed_groups(expanded_width) == frozenset()
    first = dialog.ribbon._target_collapsed_groups(expanded_width - 21)
    assert "CONSTRAINTS" in first
    assert dialog.ribbon._target_collapsed_groups(1) == frozenset(titles)

    # Rebuilding the responsive ribbon must synchronously detach old groups;
    # otherwise deleteLater() can leave the previous buttons painted on top of
    # the collapsed state during resize.
    old_groups = tuple(dialog.ribbon._group_widgets)
    dialog.ribbon._refresh_responsive_layout(1)
    assert dialog.ribbon._collapsed_titles == frozenset(titles)
    assert all(group.parent() is None for group in old_groups)
    assert len(dialog.ribbon._group_widgets) == 5

    # Commit/cancel, solver status, view mode and Fit all live in the one slim
    # viewport bar; the legacy footer is intentionally absent.
    assert dialog.status_label.parent() is bar
    assert dialog.buttons.parent() is bar
    assert dialog.view_sketch.parent() is bar
    assert dialog.view_preview.parent() is bar
    assert dialog.fit_button.parent() is bar

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
