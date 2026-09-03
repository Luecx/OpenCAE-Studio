"""Regression coverage for viewport chrome, orbit feedback and result cuts."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from opencae.ui.core.theme import PALETTE
from opencae.ui.ribbon.result_section import ResultSectionButton
from opencae.ui.viewport.viewport_canvas import ViewportCanvas


ROOT = Path(__file__).resolve().parents[1]
_QT_APPLICATION: QApplication | None = None


def _application() -> QApplication:
    global _QT_APPLICATION
    _QT_APPLICATION = QApplication.instance() or QApplication([])
    return _QT_APPLICATION


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_viewport_canvas_matches_renderer_background_behind_rounded_overlays():
    """Rounded Qt panel corners expose the same color used by the VTK renderer."""
    _application()
    canvas = ViewportCanvas()
    try:
        stylesheet = canvas.styleSheet().replace(" ", "").lower()
        assert "qwidget#viewportcanvas" in stylesheet
        assert PALETTE["viewport"].lower() in stylesheet
        assert "def refresh_theme(self)" in _source(
            "opencae/ui/viewport/viewport_canvas.py"
        )
    finally:
        canvas.deleteLater()


def test_scene_clear_invalidates_removed_vtk_rotation_pivot():
    """Results/base-scene rebuilds must recreate the transient pivot actor."""
    source = _source("opencae/ui/viewport/safe_qt_interactor.py")
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
    _application()
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
        section.deleteLater()


def test_section_controller_tracks_auto_origin_and_manual_plane_drags():
    source = _source("opencae/ui/viewport/section_view.py")

    assert '"origin_auto": True' in source
    assert 'incoming.get("origin_auto", incoming_origin is None)' in source
    assert 'if self._state["origin_auto"] or origin is None:' in source
    assert 'if self._state["origin_auto"]:' in source
    assert 'self._state["origin_auto"] = False' in source


def test_preferences_no_longer_expose_a_second_theme_selector():
    source = _source("opencae/ui/preferences/general_page.py")

    assert 'settings.value("ui/theme"' not in source
    assert "self.theme" not in source
    assert '"theme":' not in source
    assert "Icon scale" in source or "Icon scale" in source.replace("scale", "scale")
