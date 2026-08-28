"""Regressions for the docked result Time Manager and transient frame blending."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pyvista as pv
from PyQt6.QtWidgets import QApplication, QRadioButton, QToolButton

from opencae.ui.panels.time_manager import (
    TimeManagerPanel,
    _playback_icon,
    current_frame_amplitude,
    frame_axis,
    frame_bracket,
)
from opencae.ui.viewport import result_visualization
from opencae.ui.viewport.result_visualization import interpolate_values


ROOT = Path(__file__).resolve().parents[1]


def _field(frame_id):
    return SimpleNamespace(
        name="STRESS",
        metadata={
            "block": "STRESS",
            "component": "SXX",
            "step_id": 1,
            "frame_id": frame_id,
        },
    )


def _grid(scalar, displacement):
    grid = pv.PolyData(np.asarray(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0))))
    grid.point_data["node_id"] = np.asarray((1, 2), dtype=np.int64)
    grid.point_data["STRESS:SXX"] = np.asarray(scalar, dtype=float)
    for key, values in zip(
        ("DISP:D1", "DISP:D2", "DISP:D3"),
        np.asarray(displacement, dtype=float).T,
    ):
        grid.point_data[key] = values
    return grid


def test_frame_axis_uses_monotonic_solver_values_as_time():
    axis, has_time = frame_axis((0.0, 0.1, 0.5, 1.0))
    assert has_time is True
    assert axis == [0.0, 0.1, 0.5, 1.0]

    axis, has_time = frame_axis((1.0, 1.0, 1.0))
    assert has_time is False
    assert axis == [1.0, 2.0, 3.0]


def test_frame_bracket_interpolates_between_nonuniform_time_values():
    left, right, alpha = frame_bracket((0.0, 0.1, 0.5, 1.0), 0.3)
    assert (left, right) == (1, 2)
    assert np.isclose(alpha, 0.5)


def test_current_frame_mode_runs_complete_signed_sine_cycle():
    assert np.isclose(current_frame_amplitude(0.0), 0.0)
    assert np.isclose(current_frame_amplitude(0.25), 1.0)
    assert np.isclose(current_frame_amplitude(0.5), 0.0, atol=1.0e-12)
    assert np.isclose(current_frame_amplitude(0.75), -1.0)
    assert np.isclose(current_frame_amplitude(1.0), 0.0, atol=1.0e-12)


def test_interpolate_values_is_linear_and_does_not_mutate_source_arrays():
    first = np.asarray((0.0, 10.0))
    second = np.asarray((10.0, 30.0))
    blended = interpolate_values(first, second, 0.25)
    assert np.allclose(blended, (2.5, 15.0))
    assert np.allclose(first, (0.0, 10.0))
    assert np.allclose(second, (10.0, 30.0))


def test_animation_blends_displayed_scalar_and_displacement_with_same_alpha():
    first = _grid(
        (0.0, 10.0),
        ((0.0, 0.0, 0.0), (0.0, 2.0, 0.0)),
    )
    second = _grid(
        (20.0, 30.0),
        ((2.0, 0.0, 0.0), (0.0, 4.0, 0.0)),
    )
    old_loader = result_visualization._LOADER
    result_visualization._LOADER = SimpleNamespace(
        pyvista_grid=lambda *_args, **_kwargs: second.copy(deep=True)
    )
    try:
        blended = result_visualization._animated_grid(
            first,
            SimpleNamespace(source_file="dummy.frd"),
            _field(1),
            {
                "_animation": {
                    "mode": "interpolate",
                    "next_field": _field(2),
                    "alpha": 0.5,
                }
            },
        )
    finally:
        result_visualization._LOADER = old_loader

    assert np.allclose(blended.point_data["STRESS:SXX"], (10.0, 20.0))
    assert np.allclose(blended.point_data["DISP:D1"], (1.0, 0.0))
    assert np.allclose(blended.point_data["DISP:D2"], (0.0, 3.0))
    deformed = result_visualization._deformed(
        blended,
        {"deform": True, "scale": 1.0},
    )
    assert np.allclose(deformed.points[0], (1.0, 0.0, 0.0))
    assert np.allclose(deformed.points[1], (1.0, 3.0, 0.0))


def test_current_frame_factor_scales_values_and_deformation_together():
    grid = _grid(
        (10.0, 20.0),
        ((2.0, 0.0, 0.0), (0.0, 4.0, 0.0)),
    )
    scaled = result_visualization._animated_grid(
        grid,
        SimpleNamespace(source_file="dummy.frd"),
        _field(1),
        {"_animation": {"mode": "factor", "factor": 0.25}},
    )
    assert np.allclose(scaled.point_data["STRESS:SXX"], (2.5, 5.0))
    assert np.allclose(scaled.point_data["DISP:D1"], (0.5, 0.0))
    assert np.allclose(scaled.point_data["DISP:D2"], (0.0, 1.0))


def test_current_frame_negative_factor_reverses_values_and_deformation():
    grid = _grid(
        (10.0, 20.0),
        ((2.0, 0.0, 0.0), (0.0, 4.0, 0.0)),
    )
    scaled = result_visualization._animated_grid(
        grid,
        SimpleNamespace(source_file="dummy.frd"),
        _field(1),
        {"_animation": {"mode": "factor", "factor": -0.25}},
    )
    assert np.allclose(scaled.point_data["STRESS:SXX"], (-2.5, -5.0))
    assert np.allclose(scaled.point_data["DISP:D1"], (-0.5, 0.0))
    assert np.allclose(scaled.point_data["DISP:D2"], (0.0, -1.0))


def test_animation_path_updates_existing_result_actor_without_scene_clear():
    source = (ROOT / "opencae/ui/viewport/solution_scene.py").read_text(encoding="utf-8")
    animation_path = source.split(
        'animation = dict(options.get("_animation", {}) or {})', 1
    )[1].split("camera = camera_position", 1)[0]
    assert "update_result(" in animation_path
    assert "scene.clear(" not in animation_path


def test_time_manager_uses_left_sidebar_custom_icons_and_full_plot():
    app = QApplication.instance() or QApplication([])
    panel = TimeManagerPanel()
    try:
        assert isinstance(panel.current_frame, QRadioButton)
        assert isinstance(panel.across_frames, QRadioButton)
        assert panel.across_frames.isChecked()
        assert isinstance(panel.play_button, QToolButton)
        assert isinstance(panel.stop_button, QToolButton)
        assert panel.sidebar.width() == 178
        assert panel.layout().count() == 2
        assert panel.plot.minimumHeight() >= 150
        assert panel.speed.minimum() == 0.25
        assert panel.speed.maximum() == 4.0
        for kind in ("first", "previous", "play", "stop", "next", "last", "loop"):
            assert not _playback_icon(kind).isNull()
    finally:
        panel.deleteLater()
        app.processEvents()

    source = (ROOT / "opencae/ui/panels/time_manager.py").read_text(encoding="utf-8")
    assert "QStyle.StandardPixmap" not in source
    assert "_playback_icon" in source
    assert 'x_label="Time" if self._has_time_axis else "Frame"' in source
    assert 'y_label="Value"' in source
    assert "show_markers=False" in source


def test_lower_workspaces_are_independent_native_docks():
    dock_source = (ROOT / "opencae/ui/docks/output_dock.py").read_text(encoding="utf-8")
    layout_source = (ROOT / "opencae/app/window_layout.py").read_text(encoding="utf-8")
    menu_source = (ROOT / "opencae/ui/menus/window_menu.py").read_text(encoding="utf-8")

    assert "class JobsDock" in dock_source
    assert "class LogDock" in dock_source
    assert "class TimeManagerDock" in dock_source
    assert "QTabWidget" not in dock_source
    assert "OutputDock" not in dock_source
    assert "window.jobs_dock" in layout_source
    assert "window.log_dock" in layout_source
    assert "window.time_manager_dock" in layout_source
    assert "tabifyDockWidget" in layout_source
    assert "A.SHOW_JOBS" in menu_source
    assert "A.SHOW_LOG" in menu_source
    assert "A.SHOW_TIME_MANAGER" in menu_source
