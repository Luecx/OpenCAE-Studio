"""Regression coverage for profile preview rendering and dialog wiring."""

from __future__ import annotations

import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication, QTableWidget

from opencae.model.entities.profiles.calculations import (
    profile_parameters,
    profile_properties,
)
from opencae.ui.dialogs.profile import PROFILE_TYPES, ProfileDialog
from opencae.ui.dialogs.profile_preview_widget import ProfilePreviewWidget


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


def test_graph_table_changes_update_preview_state(application):
    """Propagate graph cell edits and row removal through the same refresh path."""
    dialog = ProfileDialog(initial_type="Graph profile")
    editor = dialog._editors["graph"]

    editor.nodes.item(0, 1).setText("-13")
    assert "1,-13,0" in dialog.preview.dimensions["nodes"]

    editor.segments.removeRow(0)
    assert dialog.preview.dimensions["segments"] == ""


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
