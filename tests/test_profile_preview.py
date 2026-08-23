"""Regression coverage for profile preview rendering and dialog wiring."""

from __future__ import annotations

import math
import os
from collections import Counter

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication, QTableWidget

from opencae.model.entities.profiles.calculations import (
    profile_parameters,
    profile_properties,
)
from opencae.ui.dialogs.profile import PROFILE_TYPES, ProfileDialog
from opencae.ui.dialogs.profile_parameter_limits import (
    PROFILE_DIMENSION_MAXIMUM,
)
from opencae.ui.dialogs.profile_preview_drawing import fitted_profile_rect
from opencae.ui.dialogs.profile_preview_graph import render_graph_profile
from opencae.ui.dialogs.profile_preview_widget import ProfilePreviewWidget
from opencae.ui.templates import FieldLabel


_QT_APPLICATION = None


@pytest.fixture(scope="module")
def application():
    """Provide the single offscreen Qt application required by widget tests."""
    global _QT_APPLICATION
    _QT_APPLICATION = QApplication.instance() or QApplication([])
    return _QT_APPLICATION


def _dimensions(profile_type: str) -> dict:
    """Return the calculation registry's actual defaults for one profile type."""
    return {
        key: default
        for key, _label, default in profile_parameters(profile_type)
    }


@pytest.mark.parametrize("profile_type", PROFILE_TYPES)
def test_every_profile_preview_renders_without_exception(application, profile_type):
    """Render every dialog profile type into an offscreen raster target."""
    widget = ProfilePreviewWidget(profile_type, _dimensions(profile_type))
    widget.resize(480, 230)
    image = QImage(widget.size(), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)

    widget.render(image)

    assert not image.isNull()


@pytest.mark.parametrize(
    ("nodes", "segments"),
    (
        ("", ""),
        ("1,,\ninvalid", "1,2,"),
        ("1,nan,0\n2,10,0", "1,2,-1"),
        (None, None),
    ),
)
def test_incomplete_graph_data_does_not_crash_preview(
    application,
    nodes,
    segments,
):
    """Keep partially edited graph rows safe throughout offscreen painting."""
    widget = ProfilePreviewWidget(
        "Graph profile",
        {"nodes": nodes, "segments": segments},
    )
    widget.resize(480, 230)
    image = QImage(widget.size(), QImage.Format.Format_ARGB32_Premultiplied)

    widget.render(image)

    assert widget.profile_type == "Graph profile"


def test_profile_type_switch_updates_preview_state(application):
    """Propagate the selector's active type and rebuilt defaults to the preview."""
    dialog = ProfileDialog(initial_type="Rectangle")

    dialog.kind.setCurrentText("Pipe")

    assert dialog.preview.profile_type == "Pipe"
    assert dialog.preview.dimensions == _dimensions("Pipe")


def test_dimension_change_updates_preview_state(application):
    """Propagate NumericUnitInput values through the unified refresh path."""
    dialog = ProfileDialog(initial_type="Rectangle")

    dialog._editors["width"].setValue(73.5)

    assert dialog.preview.dimensions["width"] == pytest.approx(73.5)


def test_input_labels_share_preview_dimension_symbols(application):
    """Make drawing abbreviations discoverable beside their numeric inputs."""
    dialog = ProfileDialog(initial_type="I-profile")
    labels = {label.text() for label in dialog.findChildren(FieldLabel)}

    assert "Overall height (h)" in labels
    assert "Flange width (b)" in labels
    assert "Web thickness (tw)" in labels
    assert "Flange thickness (tf)" in labels


def test_profile_dimensions_and_dependent_thicknesses_are_bounded(application):
    """Clamp section dimensions without showing a validation-error workflow."""
    dialog = ProfileDialog(initial_type="I-profile")
    assert dialog._editors["height"].editor.maximum() == PROFILE_DIMENSION_MAXIMUM

    dialog._editors["flange_width"].setValue(12.0)
    dialog._editors["web_thickness"].setValue(20.0)
    dialog._editors["height"].setValue(18.0)
    dialog._editors["flange_thickness"].setValue(20.0)

    assert dialog._editors["web_thickness"].value() == pytest.approx(12.0)
    assert dialog._editors["flange_thickness"].value() == pytest.approx(9.0)
    assert dialog.preview.dimensions["web_thickness"] == pytest.approx(12.0)
    assert dialog.preview.dimensions["flange_thickness"] == pytest.approx(9.0)


def test_graph_table_changes_update_preview_state(application):
    """Propagate graph cell edits and row removal through the same refresh path."""
    dialog = ProfileDialog(initial_type="Graph profile")
    editor = dialog._editors["graph"]

    editor.nodes.item(0, 1).setText("-13")
    assert "1,-13,0" in dialog.preview.dimensions["nodes"]

    editor.segments.removeRow(0)
    assert dialog.preview.dimensions["segments"] == ""


def test_graph_preview_uses_one_scale_for_length_and_thickness(application):
    """Preserve a graph segment's 10:1 model aspect ratio in painted pixels."""
    image = QImage(500, 240, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    render_graph_profile(
        painter,
        QRectF(0.0, 0.0, 500.0, 240.0),
        {
            "nodes": "1,0,0\n2,100,0",
            "segments": "1,2,10",
        },
    )
    painter.end()

    pixels = [
        (image.pixelColor(x, y).getRgb(), x, y)
        for y in range(image.height())
        for x in range(image.width())
    ]
    colors = Counter(color for color, _x, _y in pixels if color[3])
    section_fill = colors.most_common(1)[0][0]
    section_pixels = [
        (x, y) for color, x, y in pixels if color == section_fill
    ]
    painted_length = max(x for x, _y in section_pixels) - min(
        x for x, _y in section_pixels
    ) + 1
    painted_thickness = max(y for _x, y in section_pixels) - min(
        y for _x, y in section_pixels
    ) + 1

    assert painted_length / painted_thickness == pytest.approx(10.0, rel=0.05)


def test_parametric_preview_fit_preserves_dimension_ratio():
    """Preserve extreme parameter ratios without visual beautification."""
    profile = fitted_profile_rect(QRectF(0.0, 0.0, 500.0, 240.0), 100.0, 10.0)

    assert profile.width() / profile.height() == pytest.approx(10.0)


def test_profile_properties_remain_connected_to_calculation_values(application):
    """Keep Area, centroid, inertia, and torsion fields on calculation outputs."""
    dialog = ProfileDialog(initial_type="Circle")
    dialog._editors["diameter"].setValue(20.0)
    expected = profile_properties("Circle", {"diameter": 20.0})

    for key, expected_value in expected.items():
        displayed = float(dialog.properties._values[key].value_label.text())
        assert displayed == pytest.approx(expected_value, rel=1e-7)
    assert expected["Area"] == pytest.approx(math.pi * 100.0)


def test_parametric_properties_area_contains_no_table_widget(application):
    """Prevent the removed property table from returning for normal profiles."""
    dialog = ProfileDialog(initial_type="Rectangle")

    assert dialog.properties.findChildren(QTableWidget) == []
