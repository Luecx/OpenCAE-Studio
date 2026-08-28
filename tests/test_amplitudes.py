"""Amplitude sampling, object references, and persistence regressions."""

from __future__ import annotations

import pytest

from opencae.model.entities.amplitudes import Amplitude, sample_function
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

    expected = [(0.0, 1.0), (0.25, 3.0), (0.5, 1.0), (0.75, -1.0), (1.0, 1.0)]
    assert len(points) == len(expected)
    for point, expected_point in zip(points, expected):
        assert point == pytest.approx(expected_point)
    with pytest.raises(ValueError, match="greater than start"):
        sample_function("Ramp", None, 1.0, 1.0, 10)


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
