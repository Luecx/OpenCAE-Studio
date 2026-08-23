"""Headless behavior checks for the topology convergence visualization."""

import os
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication

from opencae.model.entities.optimization import OptimizationIteration
from opencae.ui.monitors.topology_convergence_plot import TopologyConvergencePlot
from opencae.ui.viewport.viewport_text_box import apply_viewport_text_box

_APPLICATION = None


def _application() -> QApplication:
    """Keep one QApplication alive for offscreen widget rendering."""
    global _APPLICATION
    _APPLICATION = QApplication.instance() or QApplication([])
    return _APPLICATION


def test_convergence_plot_renders_objective_and_constraint_history():
    _application()
    plot = TopologyConvergencePlot()
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


def test_viewport_text_box_enables_background_and_frame():
    actor = MagicMock()
    text_property = actor.GetTextProperty.return_value

    apply_viewport_text_box(actor)

    text_property.SetBackgroundOpacity.assert_called_once_with(0.92)
    text_property.SetFrame.assert_called_once_with(True)
