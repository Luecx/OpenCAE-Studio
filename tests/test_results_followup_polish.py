"""Regression coverage for result-monitor and animation presentation polish."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from PyQt6.QtWidgets import QApplication

from opencae.ui.panels.time_manager_contours import (
    animation_scalar_factor,
    scaled_animation_range,
    waveform_factor_extrema,
)
from opencae.ui.ribbon.result_range import _range_fit_icon


ROOT = Path(__file__).resolve().parents[1]


def _field(component):
    return SimpleNamespace(metadata={"component": component})


def test_full_sine_animation_envelope_respects_scalar_semantics():
    factors = waveform_factor_extrema(0.0, 1.0, "Sine")

    assert min(factors) == pytest.approx(-1.0)
    assert max(factors) == pytest.approx(1.0)
    assert scaled_animation_range((10.0, 80.0), _field("SXX"), factors) == pytest.approx(
        (-80.0, 80.0)
    )
    assert scaled_animation_range((10.0, 80.0), _field("Magnitude"), factors) == pytest.approx(
        (0.0, 80.0)
    )
    assert scaled_animation_range((2.0, 120.0), _field("Mises"), factors) == pytest.approx(
        (0.0, 120.0)
    )


def test_negative_factor_keeps_invariants_unsigned():
    assert animation_scalar_factor(_field("SXX"), -0.75) == pytest.approx(-0.75)
    assert animation_scalar_factor(_field("Magnitude"), -0.75) == pytest.approx(0.75)
    assert animation_scalar_factor(_field("Mises"), -0.75) == pytest.approx(0.75)


def test_contour_fit_icons_are_distinct():
    app = QApplication.instance() or QApplication([])
    frame = _range_fit_icon("frame", 16)
    frames = _range_fit_icon("frames", 16)
    animation = _range_fit_icon("animation", 16)

    assert app is not None
    assert not frame.isNull()
    assert not frames.isNull()
    assert not animation.isNull()
    assert len({frame.cacheKey(), frames.cacheKey(), animation.cacheKey()}) == 3


def test_analysis_monitor_exposes_job_scoped_open_results_action():
    source = (ROOT / "opencae/ui/monitors/analysis_job_monitor.py").read_text(
        encoding="utf-8"
    )
    assert '"Open Results"' in source
    assert '"Preparing Results…"' in source
    assert "changed.connect(self._refresh_results_button)" in source
    assert "def _available_result(self):" in source
    assert "def _open_results(self):" in source
    assert "show_solution(result)" in source


def test_physical_beam_toggle_preserves_camera_by_contract():
    source = (ROOT / "opencae/ui/viewport/beam_physical_display.py").read_text(
        encoding="utf-8"
    )
    method = source.split("def set_enabled", 1)[1].split("def prepare_options", 1)[0]
    assert "camera = camera_position(self.viewport.plotter)" in method
    assert "restore_camera(self.viewport.plotter, camera)" in method
    assert "finally:" in method


def test_contour_editor_hosts_animation_envelope_action():
    source = (ROOT / "opencae/ui/ribbon/result_range.py").read_text(encoding="utf-8")
    assert '"Fit animation envelope"' in source
    assert "animation_envelope_requested" in source
    assert '_range_fit_icon("frame", 16)' not in source  # scope is passed dynamically
    assert "_range_fit_icon(scope, 16)" in source
