from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from opencae.geometry import GeometryService
from opencae.geometry.cache import CACHE
from opencae.model.entities.geometry import (
    SketchDefinition,
    SketchFeature,
    SketchFeatureMode,
    SketchLine,
    SketchPoint,
)
from opencae.model.entities.parts import Part


ROOT = Path(__file__).resolve().parents[1]


def _revolve_part() -> Part:
    sketch = SketchDefinition()
    points = [
        SketchPoint(x=0.0, y=2.0),
        SketchPoint(x=8.0, y=2.0),
        SketchPoint(x=8.0, y=4.0),
        SketchPoint(x=0.0, y=4.0),
    ]
    sketch.points.extend(points)
    sketch.entities.extend(
        (
            SketchLine(start=points[0], end=points[1]),
            SketchLine(start=points[1], end=points[2]),
            SketchLine(start=points[2], end=points[3]),
            SketchLine(start=points[3], end=points[0]),
        )
    )
    return Part(
        name="Revolved mesh",
        geometry=[
            SketchFeature(
                name="Revolve",
                mode=SketchFeatureMode.REVOLVE,
                sketch=sketch,
                angle_degrees=360.0,
            )
        ],
    )


def test_revolved_solid_quality_ignores_lower_dimensional_gmsh_boundary_elements():
    part = _revolve_part()
    try:
        snapshot = GeometryService().generate_mesh(part)
        assert snapshot.dimension == 3
        # A generated 3D Gmsh model legitimately contains boundary edge and
        # surface elements as well as volume elements. Type 1 is the ordinary
        # 2-node Gmsh line element and must not be treated as an FE-volume
        # quality candidate.
        assert any(block.dimension < snapshot.dimension for block in snapshot.blocks)
        assert any(block.gmsh_type == 1 for block in snapshot.blocks)

        top_blocks = [
            block for block in snapshot.blocks if block.dimension == snapshot.dimension
        ]
        top_count = sum(len(block.element_tags) for block in top_blocks)
        assert top_count > 0
        assert snapshot.qualities is not None
        assert len(snapshot.qualities) == top_count
        assert all(float(value) >= 0.0 for value in snapshot.qualities)
    finally:
        CACHE.invalidate(part.id)


_PREVIEW_TEARDOWN_SMOKE = r'''
from PyQt6.QtWidgets import QApplication, QDialog, QWidget

import opencae.ui.sketcher.preview as preview_module


class FakePlotter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.closed_by_preview = False

    def set_background(self, *_args, **_kwargs):
        pass

    def close(self):
        self.closed_by_preview = True
        return super().close()


app = QApplication.instance() or QApplication([])
preview_module.SafeQtInteractor = FakePlotter
parent = QDialog()
preview = preview_module.SketchFeaturePreview(parent)
# No native render surface is created while the Sketch page is active. This is
# important on Windows, where hidden QVTK children can otherwise acquire HWND/
# WGL resources and interfere with sibling widget stacking.
assert preview.plotter is None
plotter = preview._ensure_plotter()
assert plotter is preview.plotter
assert not plotter.closed_by_preview
parent.reject()
app.processEvents()
assert plotter.closed_by_preview
# shutdown is intentionally idempotent because Qt may send close again later.
preview.shutdown()
assert plotter.closed_by_preview
'''


def test_sketch_preview_closes_render_surface_when_parent_dialog_finishes():
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["PYVISTA_OFF_SCREEN"] = "true"
    result = subprocess.run(
        [sys.executable, "-c", _PREVIEW_TEARDOWN_SMOKE],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout
