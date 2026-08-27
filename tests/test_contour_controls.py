"""Regressions for result contour controls and coordinate-system overlays."""

from pathlib import Path

import numpy as np
from PyQt6.QtWidgets import QApplication, QCheckBox, QRadioButton, QToolButton

from opencae.ui.ribbon.result_deformation import ResultDeformationButton
from opencae.ui.ribbon.result_range import ResultRangeButton
from opencae.ui.ribbon.result_section import ResultSectionButton
from opencae.ui.viewport.contour_mapping import (
    CONTINUOUS_COLOR_COUNT,
    DEFAULT_CONTOUR_LEVELS,
    DEFAULT_OUTSIDE_COLOR,
    MAX_CONTOUR_LEVELS,
    MIN_CONTOUR_LEVELS,
    contour_plot_kwargs,
)
from opencae.ui.viewport.coordinate_system_overlay import (
    CoordinateSystemOverlay,
    _ring_geometry,
)


ROOT = Path(__file__).resolve().parents[1]


def test_contour_mapping_keeps_discrete_mode_as_default():
    mapping = contour_plot_kwargs({})
    assert mapping == {
        "n_colors": DEFAULT_CONTOUR_LEVELS,
        "below_color": DEFAULT_OUTSIDE_COLOR,
        "above_color": DEFAULT_OUTSIDE_COLOR,
    }


def test_contour_mapping_supports_continuous_and_disabled_outside_colors():
    mapping = contour_plot_kwargs(
        {
            "continuous": True,
            "levels": 7,
            "outside_colors": False,
            "below_color": "#111111",
            "above_color": "#eeeeee",
        }
    )
    assert mapping == {
        "n_colors": CONTINUOUS_COLOR_COUNT,
        "below_color": None,
        "above_color": None,
    }


def test_contour_mapping_clamps_discrete_level_count_to_52():
    assert MAX_CONTOUR_LEVELS == 52
    assert contour_plot_kwargs({"levels": 0})["n_colors"] == MIN_CONTOUR_LEVELS
    assert contour_plot_kwargs({"levels": 999})["n_colors"] == 52


def test_result_range_button_uses_checkboxes_and_full_contour_configuration():
    app = QApplication.instance() or QApplication([])
    button = ResultRangeButton()
    try:
        assert isinstance(button.continuous, QCheckBox)
        assert isinstance(button.outside_colors, QCheckBox)
        assert button.levels.maximum() == 52
        assert button.below_color.text() == ""
        assert button.above_color.text() == ""
        assert button.below_color.toolTip() == "Below-range color"
        assert button.above_color.toolTip() == "Above-range color"
        assert button.below_color.width() <= 40
        assert button.above_color.width() <= 40
        button.set_data_range(-3.0, 12.0)
        assert button.values()["minimum"] == -3.0
        assert button.values()["maximum"] == 12.0
        assert button.values()["levels"] == DEFAULT_CONTOUR_LEVELS
        assert button.values()["continuous"] is False
        assert button.values()["outside_colors"] is True

        button.levels.setValue(52)
        button.continuous.setChecked(True)
        button.outside_colors.setChecked(False)
        values = button.values()
        assert values["levels"] == 52
        assert values["continuous"] is True
        assert values["outside_colors"] is False
        assert button.levels.isEnabled() is False
        assert button.below_color.isEnabled() is False
        assert button.above_color.isEnabled() is False
    finally:
        button.deleteLater()
        app.processEvents()


def test_deformation_and_section_buttons_open_instant_popups_with_radio_state():
    app = QApplication.instance() or QApplication([])
    deformation = ResultDeformationButton()
    section = ResultSectionButton()
    try:
        for button in (deformation, section):
            assert button.popupMode() == QToolButton.ToolButtonPopupMode.InstantPopup
            assert not button.isCheckable()
        assert isinstance(deformation.enabled, QRadioButton)
        assert isinstance(deformation.disabled, QRadioButton)
        assert isinstance(section.section_on, QRadioButton)
        assert isinstance(section.section_off, QRadioButton)
        assert deformation.values()[0] is False
        assert section.values()["enabled"] is False
        deformation.enabled.setChecked(True)
        section.section_on.setChecked(True)
        assert deformation.values()[0] is True
        assert section.values()["enabled"] is True
    finally:
        deformation.deleteLater()
        section.deleteLater()
        app.processEvents()


def test_cylindrical_ring_geometry_respects_origin_normal_and_radius():
    origin = np.asarray((1.0, 2.0, 3.0))
    ring = _ring_geometry(origin, (0.0, 0.0, 1.0), 2.0)
    offsets = np.asarray(ring.points) - origin
    assert len(ring.points) >= 72
    assert np.allclose(offsets[:, 2], 0.0, atol=1.0e-10)
    assert np.allclose(np.linalg.norm(offsets[:, :2], axis=1), 2.0, atol=1.0e-8)


def test_coordinate_overlay_observes_camera_for_screen_space_rescaling():
    class Camera:
        def __init__(self):
            self.callback = None

        def AddObserver(self, event, callback):
            assert event == "ModifiedEvent"
            self.callback = callback
            return 9

    class Plotter:
        camera = Camera()

    overlay = CoordinateSystemOverlay()
    plotter = Plotter()
    overlay._observe_camera(plotter)
    assert plotter.camera.callback is not None
    assert overlay._observer_id == 9


def test_ribbon_dropdown_style_has_arrow_without_split_button_border():
    source = (ROOT / "opencae/ui/core/styles/buttons.py").read_text(encoding="utf-8")
    assert 'QToolButton[ribbonButton="true"]::menu-button' in source
    assert "border: none;" in source
    assert 'QToolButton[ribbonButton="true"]::menu-indicator' in source
    assert "subcontrol-position: bottom right;" in source
