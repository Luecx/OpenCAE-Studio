"""Regressions for result contour controls and coordinate-system overlays."""

from pathlib import Path

import numpy as np
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLabel,
    QRadioButton,
    QSizePolicy,
    QToolButton,
    QWidget,
)

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


def test_result_range_button_uses_bound_auto_icons_labels_and_symmetry_link():
    app = QApplication.instance() or QApplication([])
    button = ResultRangeButton()
    try:
        assert isinstance(button.continuous, QCheckBox)
        assert isinstance(button.outside_colors, QCheckBox)
        assert button.levels.maximum() == 52

        auto_buttons = (
            button.minimum_frame,
            button.minimum_frames,
            button.maximum_frame,
            button.maximum_frames,
        )
        for auto in auto_buttons:
            assert isinstance(auto, QToolButton)
            assert not auto.isCheckable()
            assert auto.text() == ""
            assert not auto.icon().isNull()
        assert "current frame" in button.minimum_frame.toolTip().lower()
        assert "all frames" in button.minimum_frames.toolTip().lower()
        assert "current frame" in button.maximum_frame.toolTip().lower()
        assert "all frames" in button.maximum_frames.toolTip().lower()
        assert button.minimum_frame.parent() is button.minimum.parent()
        assert button.minimum_frames.parent() is button.minimum.parent()
        assert button.maximum_frame.parent() is button.maximum.parent()
        assert button.maximum_frames.parent() is button.maximum.parent()

        assert button.symmetric.isCheckable()
        assert not button.symmetric.icon().isNull()
        assert "symmetrically" in button.symmetric.toolTip().lower()

        labels = {
            label.text()
            for label in button.findChildren(QLabel)
            if label.text()
        }
        assert "Below range" in labels
        assert "Above range" in labels
        separators = button.findChildren(QWidget, "ResultRangeSeparator")
        assert len(separators) == 2

        assert button.below_color.text() == ""
        assert button.above_color.text() == ""
        assert button.below_color.toolTip() == "Below-range color"
        assert button.above_color.toolTip() == "Above-range color"
        assert button.below_color.minimumWidth() >= 72
        assert button.above_color.minimumWidth() >= 72
        assert (
            button.below_color.sizePolicy().horizontalPolicy()
            == QSizePolicy.Policy.Expanding
        )
        assert (
            button.above_color.sizePolicy().horizontalPolicy()
            == QSizePolicy.Policy.Expanding
        )

        button.set_data_range(-3.0, 12.0)
        # Remembering frame data must not silently overwrite a concrete/manual
        # range. A bound icon is a one-shot calculation action.
        assert button.values()["minimum"] == 0.0
        assert button.values()["maximum"] == 0.0
        button.apply_data_range()
        values = button.values()
        assert values["minimum"] == -3.0
        assert values["maximum"] == 12.0
        assert values["minimum_auto"] is False
        assert values["maximum_auto"] is False
        assert values["symmetric"] is False

        # Bound-specific calculations leave the opposite side untouched while
        # uncoupled.
        button.set_bound("minimum", -4.0)
        assert button.minimum.value() == -4.0
        assert button.maximum.value() == 12.0
        button.set_bound("maximum", 9.0)
        assert button.minimum.value() == -4.0
        assert button.maximum.value() == 9.0

        # Linking first normalizes the envelope, then either editor mirrors the
        # opposite bound with the same magnitude and inverse sign.
        button.symmetric.setChecked(True)
        assert button.minimum.value() == -9.0
        assert button.maximum.value() == 9.0
        button.minimum.setValue(-5.0)
        assert button.minimum.value() == -5.0
        assert button.maximum.value() == 5.0
        button.maximum.setValue(8.0)
        assert button.minimum.value() == -8.0
        assert button.maximum.value() == 8.0
        button.set_bound("minimum", -2.5)
        assert button.minimum.value() == -2.5
        assert button.maximum.value() == 2.5
        assert button.values()["symmetric"] is True

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

    source = (ROOT / "opencae/ui/ribbon/result_range.py").read_text(encoding="utf-8")
    assert 'SectionHeading("Range")' in source
    assert 'SectionHeading("Color Mapping")' in source
    assert 'SectionHeading("Outside Range")' in source
    assert source.count("ResultRangeSeparator") >= 2
    assert '"Auto Frame"' not in source
    assert '"Auto Frames"' not in source
    assert "minimum_auto.toggled" not in source
    assert "maximum_auto.toggled" not in source


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

        assert deformation.auto_frame.text() == "Current Frame"
        assert deformation.auto_frames.text() == "All Frames"
        assert "current frame" in deformation.auto_frame.toolTip().lower()
        assert "all frames" in deformation.auto_frames.toolTip().lower()

        # Very large physical displacements can produce tiny automatic display
        # factors. They must survive the editor instead of rounding to zero.
        assert deformation.scale.editor.decimals() >= 12
        deformation.set_scale(1.23456789e-9)
        assert deformation.values()[1] > 0.0
        assert np.isclose(deformation.values()[1], 1.23456789e-9, rtol=0.0, atol=1e-15)
    finally:
        deformation.deleteLater()
        section.deleteLater()
        app.processEvents()

    section_source = (ROOT / "opencae/ui/ribbon/result_section.py").read_text(encoding="utf-8")
    assert "Align normal" not in section_source
    assert "_set_axis" not in section_source
    assert 'SectionHeading("Plane")' in section_source


def test_radio_buttons_use_application_theme_indicator():
    source = (ROOT / "opencae/ui/core/styles/fields.py").read_text(encoding="utf-8")
    assert "QRadioButton::indicator" in source
    assert "border-radius: 9px" in source
    assert "qradialgradient" in source
    assert "QRadioButton::indicator:checked:hover" in source


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
