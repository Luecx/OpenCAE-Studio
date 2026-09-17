"""Headless behavior checks for the topology convergence visualization."""

import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import MagicMock

from opencae.ui.other.viewport.viewport_text_box import apply_viewport_text_box


ROOT = Path(__file__).resolve().parents[1]


def test_convergence_plot_renders_objective_and_constraint_history():
    # Rendering is intentionally exercised in a fresh Qt process. Earlier tests
    # create and destroy VTK/QOpenGLWidget contexts; keeping this painter-only
    # widget smoke isolated prevents unrelated native context lifetime from
    # affecting the convergence plot while still testing a real render pass.
    script = r'''
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication
from opencae.model.entities.optimization import OptimizationIteration
from opencae.ui.other.monitors.topology_convergence_plot import TopologyConvergencePlot

app = QApplication.instance() or QApplication([])
plot = TopologyConvergencePlot()
try:
    plot.resize(760, 460)
    plot.set_iterations(
        [
            OptimizationIteration(
                name="Iteration-1",
                number=1,
                objective_value=12.0,
                constraint_values={"volume": 0.42},
            ),
            OptimizationIteration(
                name="Iteration-2",
                number=2,
                objective_value=10.5,
                constraint_values={"volume": 0.31},
            ),
        ],
        constraint_limit=0.3,
    )
    image = QPixmap(plot.size())
    plot.render(image)
    assert not image.isNull()
    assert plot._samples() == [(1, 12.0, 0.42), (2, 10.5, 0.31)]
finally:
    plot.close()
    plot.deleteLater()
    app.processEvents()
'''
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


def test_viewport_text_box_enables_background_and_frame():
    actor = MagicMock()
    text_property = actor.GetTextProperty.return_value

    apply_viewport_text_box(actor)

    text_property.SetBackgroundOpacity.assert_called_once_with(0.92)
    text_property.SetFrame.assert_called_once_with(True)
