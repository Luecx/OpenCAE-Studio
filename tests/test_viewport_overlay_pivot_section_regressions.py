"""Regression coverage for viewport chrome, orbit feedback and result cuts."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _run_isolated_qt(script: str) -> None:
    """Run one real Qt widget probe without inherited VTK/native state."""
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


def test_viewport_canvas_matches_renderer_background_behind_rounded_overlays():
    """Rounded Qt panel corners expose the same color used by the VTK renderer."""
    _run_isolated_qt(r'''
from PyQt6.QtWidgets import QApplication
from opencae.ui.foundation.theme import PALETTE
from opencae.ui.other.viewport.viewport_canvas import ViewportCanvas

app = QApplication.instance() or QApplication([])
canvas = ViewportCanvas()
try:
    stylesheet = canvas.styleSheet().replace(" ", "").lower()
    assert "qwidget#viewportcanvas" in stylesheet
    assert PALETTE["viewport"].lower() in stylesheet
finally:
    canvas.close()
    canvas.deleteLater()
    app.processEvents()
''')
    assert "def refresh_theme(self)" in _source(
        "opencae/ui/other/viewport/viewport_canvas.py"
    )


def test_scene_clear_invalidates_removed_vtk_rotation_pivot():
    """Results/base-scene rebuilds must recreate the transient pivot actor."""
    source = _source("opencae/ui/other/viewport/safe_qt_interactor.py")
    clear_start = source.index("    def clear(self, *args, **kwargs):")
    next_method = source.index("    def refresh_theme(self)", clear_start)
    implementation = source[clear_start:next_method]

    assert "super().clear(*args, **kwargs)" in implementation
    assert "self._rotation_pivot = None" in implementation
    assert implementation.index("super().clear") < implementation.index(
        "self._rotation_pivot = None"
    )


def test_automatic_section_origin_stays_automatic_after_viewport_reports_center():
    """Resolved center coordinates must not silently become a manual cut origin."""
    _run_isolated_qt(r'''
from PyQt6.QtWidgets import QApplication
from opencae.ui.other.ribbon.result_section import ResultSectionButton

app = QApplication.instance() or QApplication([])
section = ResultSectionButton()
try:
    section.set_state(
        {
            "enabled": True,
            "origin": (10.0, 20.0, 30.0),
            "origin_auto": True,
            "normal": (1.0, 0.0, 0.0),
        }
    )
    values = section.values()
    assert values["origin_auto"] is True
    assert values["origin"] is None

    section.set_state(
        {
            "origin": (11.0, 22.0, 33.0),
            "origin_auto": False,
        }
    )
    values = section.values()
    assert values["origin_auto"] is False
    assert tuple(values["origin"]) == (11.0, 22.0, 33.0)
finally:
    section.close()
    section.deleteLater()
    app.processEvents()
''')


def test_section_controller_tracks_auto_origin_and_manual_plane_drags():
    source = _source("opencae/ui/other/viewport/section_view.py")

    assert '"origin_auto": True' in source
    assert 'incoming.get("origin_auto", incoming_origin is None)' in source
    assert 'if self._state["origin_auto"] or origin is None:' in source
    assert 'if self._state["origin_auto"]:' in source
    assert 'self._state["origin_auto"] = False' in source


def test_preferences_no_longer_expose_a_second_theme_selector():
    source = _source("opencae/ui/other/preferences/general_page.py")

    assert 'settings.value("ui/theme"' not in source
    assert "self.theme" not in source
    assert '"theme":' not in source
    assert '"appearance/color_scheme"' not in source
    assert '"ui/confirm_delete"' in source
    assert '"ui/restore_layout"' in source
