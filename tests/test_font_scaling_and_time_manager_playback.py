"""Regressions for application font scaling and Time Manager playback limits."""

from pathlib import Path

import numpy as np

from opencae.ui.core.application_preferences import _scaled_stylesheet
from opencae.ui.panels.time_manager import current_frame_amplitude


ROOT = Path(__file__).resolve().parents[1]


def test_explicit_qss_font_sizes_follow_application_scale():
    source = "QLabel { font-size: 8pt; } QPushButton { font-size: 10px; }"
    assert _scaled_stylesheet(source, 100) == source
    scaled = _scaled_stylesheet(source, 125)
    assert "font-size: 10pt" in scaled
    assert "font-size: 12.5px" in scaled


def test_current_frame_waveform_presets_have_expected_shapes():
    assert np.isclose(current_frame_amplitude(0.25, "Sine"), 1.0)
    assert np.isclose(current_frame_amplitude(0.75, "Sine"), -1.0)

    assert np.isclose(current_frame_amplitude(0.0, "Half sine"), 0.0)
    assert np.isclose(current_frame_amplitude(0.5, "Half sine"), 1.0)
    assert np.isclose(current_frame_amplitude(1.0, "Half sine"), 0.0, atol=1e-12)

    assert np.isclose(current_frame_amplitude(0.25, "Triangle"), 1.0)
    assert np.isclose(current_frame_amplitude(0.5, "Triangle"), 0.0)
    assert np.isclose(current_frame_amplitude(0.75, "Triangle"), -1.0)

    assert np.isclose(current_frame_amplitude(0.0, "Ramp"), 0.0)
    assert np.isclose(current_frame_amplitude(0.5, "Ramp"), 0.5)
    assert np.isclose(current_frame_amplitude(1.0, "Ramp"), 1.0)


def test_time_manager_exposes_drag_play_limits_and_single_frame_function_menu():
    panel_source = (ROOT / "opencae/ui/panels/time_manager.py").read_text(
        encoding="utf-8"
    )
    plot_source = (ROOT / "opencae/ui/panels/time_manager_plot.py").read_text(
        encoding="utf-8"
    )

    assert 'WAVEFORMS = ("Sine", "Half sine", "Triangle", "Ramp")' in panel_source
    assert 'self.function_row.setVisible(False)' in panel_source
    assert 'self.function_row.setVisible(self.current_frame.isChecked())' in panel_source
    assert 'QComboBox#TimeManagerFunctionSelect' in panel_source
    assert 'border: none' in panel_source
    assert 'self.plot.play_range_changed.connect(self._play_range_changed)' in panel_source
    assert 'self._play_ranges = {' in panel_source
    assert 'start, end = self._play_limits()' in panel_source

    assert 'play_range_changed = pyqtSignal(float, float)' in plot_source
    assert 'PALETTE["danger"]' in plot_source
    assert 'Qt.PenStyle.DashLine' in plot_source
    assert 'Qt.CursorShape.SizeHorCursor' in plot_source
    assert 'self._drag_boundary = boundary' in plot_source


def test_persisted_font_scale_is_reapplied_after_widget_and_theme_construction():
    app_source = (ROOT / "opencae/app/application.py").read_text(encoding="utf-8")
    preference_source = (
        ROOT / "opencae/ui/core/application_preferences.py"
    ).read_text(encoding="utf-8")
    view_source = (ROOT / "opencae/ui/menus/view_menu.py").read_text(encoding="utf-8")

    main_window_index = app_source.index("window = MainWindow(context)")
    later_apply = app_source.index(
        "apply_application_preferences(app, appearance)", main_window_index
    )
    assert later_apply > main_window_index
    assert "application.allWidgets()" in preference_source
    assert "_opencae_base_stylesheet" in preference_source
    assert "_opencae_scaled_stylesheet" in preference_source
    assert view_source.count("apply_application_preferences(app, settings)") >= 2
