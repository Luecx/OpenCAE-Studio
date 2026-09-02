"""Amplitude sampling, preview, object-reference, and persistence regressions."""

from __future__ import annotations

import pytest

from opencae.model.entities.amplitudes import (
    Amplitude,
    preview_points,
    sample_function,
)
from opencae.persistence.project_io import load_project, save_project


def test_function_amplitude_sampling_is_deterministic_and_validated():
    """Analytical presets produce a stable persisted point representation."""
    points = sample_function(
        "Sine",
        {"amplitude": 2.0, "frequency": 1.0, "phase": 0.0, "offset": 1.0},
        0.0,
        1.0,
        4,
    )

    expected = [
        (0.0, 1.0),
        (0.25, 3.0),
        (0.5, 1.0),
        (0.75, -1.0),
        (1.0, 1.0),
    ]
    assert len(points) == len(expected)
    for point, expected_point in zip(points, expected):
        assert point == pytest.approx(expected_point)
    with pytest.raises(ValueError, match="greater than start"):
        sample_function("Ramp", None, 1.0, 1.0, 10)


def test_function_ramp_is_baked_to_linear_table():
    points = sample_function(
        "Ramp",
        {"start_value": -1.0, "end_value": 3.0},
        2.0,
        4.0,
        4,
    )
    assert len(points) == 5
    assert points[0] == (2.0, -1.0)
    assert points[-1] == (4.0, 3.0)
    assert points[2] == (3.0, 1.0)


def test_smooth_step_preview_preserves_knots_and_densifies():
    knots = [(0.0, 0.0), (1.0, 1.0), (2.0, 0.5)]
    points = preview_points(knots, "Smooth Step", samples_per_segment=8)
    assert points[0] == knots[0]
    assert points[-1] == knots[-1]
    assert len(points) > len(knots)
    assert points[8] == (1.0, 1.0)


def test_amplitude_requires_strictly_increasing_time():
    with pytest.raises(ValueError, match="strictly increasing"):
        Amplitude(
            name="Invalid",
            points=[(0.0, 0.0), (0.0, 1.0)],
        )


def test_function_metadata_does_not_replace_authoritative_points():
    amplitude = Amplitude(
        name="Sine",
        points=[(0.0, 0.0), (0.5, 1.0), (1.0, 0.0)],
        source_mode="Function",
        function_type="Sine",
        function_parameters={"amplitude": 1.0, "frequency": 1.0},
    )
    assert amplitude.points == [(0.0, 0.0), (0.5, 1.0), (1.0, 0.0)]
    assert amplitude.source_mode == "Function"


def test_load_amplitude_is_an_object_reference_and_survives_roundtrip(
    tmp_path,
    project_factory,
):
    """Loads expose amplitude objects while persistence retains stable IDs."""
    project = project_factory(include_constraints=False)["project"]
    amplitude = Amplitude(name="Pulse", points=[(0.0, 0.0), (1.0, 1.0)])
    project.amplitudes.append(amplitude)
    load = project.loads[0]

    project.rebuild_index(strict=True)
    load.amplitude = amplitude
    project.rebuild_index(strict=True)
    assert load.amplitude is amplitude
    assert load.amplitude_ref.entity_id == amplitude.id

    path = tmp_path / "amplitude.ocae"
    save_project(project, path)
    loaded = load_project(path)

    assert loaded.loads[0].amplitude is loaded.amplitudes[0]
    assert loaded.loads[0].amplitude_ref.entity_id == loaded.amplitudes[0].id
