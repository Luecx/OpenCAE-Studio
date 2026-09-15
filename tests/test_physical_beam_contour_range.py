"""Regression coverage for contour ranges on expanded physical beams."""

from types import SimpleNamespace

import numpy as np

from opencae.ui.viewport.beam_physical_display import _expanded_range_settings


class _Loader:
    @staticmethod
    def scalar_range(_source, _field):
        return (-2.0, 2.0)


class _Grid:
    def __init__(self):
        self.point_data = {
            "STRESS:SXX": np.asarray((-7.5, 4.25, np.nan), dtype=float),
        }
        self.cell_data = {}


def _field():
    return SimpleNamespace(
        name="Stress",
        metadata={"block": "STRESS", "component": "SXX"},
    )


def test_expanded_beam_points_extend_default_contour_range():
    result = SimpleNamespace(source_file="results.res")
    settings = {
        "minimum": -2.0,
        "maximum": 2.0,
        "minimum_auto": False,
        "maximum_auto": False,
    }

    adjusted = _expanded_range_settings(
        _Loader(),
        result,
        _field(),
        _Grid(),
        settings,
    )

    assert adjusted["minimum"] == -7.5
    assert adjusted["maximum"] == 4.25
    assert settings["minimum"] == -2.0
    assert settings["maximum"] == 2.0


def test_expanded_beam_range_preserves_manually_changed_bound():
    result = SimpleNamespace(source_file="results.res")
    settings = {
        "minimum": -1.0,
        "maximum": 2.0,
        "minimum_auto": False,
        "maximum_auto": False,
    }

    adjusted = _expanded_range_settings(
        _Loader(),
        result,
        _field(),
        _Grid(),
        settings,
    )

    assert adjusted["minimum"] == -1.0
    assert adjusted["maximum"] == 4.25
