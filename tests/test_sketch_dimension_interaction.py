"""Regression coverage for interactive Sketcher dimensions and ribbon menus."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_ribbon_toggle_style_and_collapsed_menus_have_one_interaction_layer():
    buttons = (ROOT / "opencae/ui/core/styles/buttons.py").read_text(encoding="utf-8")
    collapsed = (ROOT / "opencae/ui/composites/collapsed_action_group.py").read_text(
        encoding="utf-8"
    )
    dialog = (ROOT / "opencae/ui/sketcher/constraint_dialog.py").read_text(
        encoding="utf-8"
    )

    assert 'QToolButton[ribbonButton="true"]:checked' in buttons
    assert "background: {p['panel_active']};" in buttons
    assert "def _leaf_actions(action: QAction)" in collapsed
    assert "leaves.extend(_leaf_actions(child))" in collapsed
    assert "for leaf in _leaf_actions(action):" in collapsed
    assert 'IconKind.PREVIOUS_FRAME' in dialog
    assert 'IconKind.NEXT_FRAME' in dialog


_DIMENSION_SMOKE = r'''
from PyQt6.QtWidgets import QApplication

from opencae.model.core import decode_model, encode_model
from opencae.model.entities.geometry import (
    SketchConstraint,
    SketchConstraintKind,
    SketchDefinition,
    SketchFeature,
)
from opencae.ui.sketcher.editor_canvas import SketchEditorCanvas

app = QApplication.instance() or QApplication([])
sketch = SketchDefinition()
line = sketch.add_line((0.0, 0.0), (20.0, 0.0))
dimension = SketchConstraint(
    kind=SketchConstraintKind.DISTANCE,
    refs=(line,),
    value=20.0,
)
sketch.constraints.append(dimension)
feature = SketchFeature(name="Dimension interaction", sketch=sketch)
layout = feature.parameters.setdefault("sketch_dimension_positions", {})
canvas = SketchEditorCanvas(feature.sketch)
canvas.resize(800, 600)
canvas.set_dimension_layout(layout)
canvas.show()
app.processEvents()
try:
    # New dimensions must begin outside the geometry bounds, not on top of the
    # measured line.
    position = canvas._dimension_position(dimension, 0)
    xmin, ymin, xmax, ymax = sketch.bounds()
    assert (
        position.x() < xmin
        or position.x() > xmax
        or position.y() < ymin
        or position.y() > ymax
    )

    # A moved annotation is presentation state on the feature and therefore
    # survives the ordinary model codec without turning into sketch topology.
    layout[dimension.id] = (35.0, 18.0)
    encoded = encode_model(feature)
    decoded = decode_model(encoded)
    assert decoded.parameters["sketch_dimension_positions"][dimension.id] == (35.0, 18.0)

    # Editing a dimension is solver-backed and stays undoable as a sketch edit.
    assert canvas.set_dimension_value(dimension.id, 30.0)
    current = next(item for item in canvas.sketch.constraints if item.id == dimension.id)
    assert current.value == 30.0
    assert canvas._history

    canvas._rebuild_scene(solve=False)
    labels = [
        item
        for item in canvas.scene().items()
        if item.data(1) == "dimension"
    ]
    assert labels
    assert "double-click" in labels[0].toolTip()
finally:
    canvas.close()
    app.processEvents()
'''


def test_dimension_labels_are_external_movable_editable_and_persistent():
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["PYVISTA_OFF_SCREEN"] = "true"
    result = subprocess.run(
        [sys.executable, "-c", _DIMENSION_SMOKE],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout
