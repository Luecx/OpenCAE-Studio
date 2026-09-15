"""Self-contained FRD beam metadata must replace all result sidecars."""

import base64
import json

import numpy as np

from opencae.results import FrdLoader
from opencae.results.frd_beam_metadata import (
    _normalize_force_ids,
    beam_normal_stress_range,
    read_frd_beam_metadata,
    section_forces_from_frd,
)


def _write_embedded_frd(path):
    payload = json.dumps(
        {"width": 4.0, "height": 2.0},
        separators=(",", ":"),
        sort_keys=True,
    )
    encoded = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    chunks = [encoded[index:index + 32] for index in range(0, len(encoded), 32)]
    lines = ["    1UOCAE SCHEMA 1"]
    lines.extend(
        f"    1UOCAE P 1 1 {index} {len(chunks)} {chunk}"
        for index, chunk in enumerate(chunks)
    )
    lines.extend(
        (
            "    1UOCAE B 7 1 0.000000000e+00 1.000000000e+00 0.000000000e+00",
            "    1UOCAE F1 1 1 7 0 8.0 2.0 3.0",
            "    1UOCAE F2 1 1 7 0 4.0 0.0 0.0",
            "    1UOCAE F1 1 1 7 1 16.0 7.0 8.0",
            "    1UOCAE F2 1 1 7 1 9.0 0.0 0.0",
        )
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_frd_user_records_round_trip_profile_n1_and_twelve_section_forces(tmp_path):
    path = tmp_path / "results.frd"
    _write_embedded_frd(path)

    metadata = read_frd_beam_metadata(path)

    assert metadata.schema == 1
    assert set(metadata.profiles) == {1}
    assert metadata.profiles[1].profile_type == "Rectangle"
    assert metadata.profiles[1].dimensions == {"height": 2.0, "width": 4.0}
    assert len(metadata.beams) == 1
    assert metadata.beams[0].solver_element_id == 7
    assert metadata.beams[0].n1 == (0.0, 1.0, 0.0)
    forces = metadata.forces[(1, 1)][7]
    assert forces.shape == (2, 6)
    np.testing.assert_allclose(forces[0], (8, 2, 3, 4, 0, 0))
    np.testing.assert_allclose(forces[1], (16, 7, 8, 9, 0, 0))


def test_embedded_beam_stress_is_exposed_as_an_frd_result_field(tmp_path):
    path = tmp_path / "results.frd"
    _write_embedded_frd(path)

    loader = FrdLoader()
    fields = loader.fields(path)

    assert len(fields) == 1
    field = fields[0]
    assert field.name == "Beam Normal Stress"
    assert field.metadata["block"] == "BEAM"
    assert field.metadata["default_component"] == "Normal Stress"
    assert field.metadata["embedded_beam_normal_stress"] is True
    np.testing.assert_allclose(loader.scalar_range(path, field), (1.0, 2.0))
    np.testing.assert_allclose(section_forces_from_frd(path, 1, 1)[7][:, 0], (8.0, 16.0))
    np.testing.assert_allclose(beam_normal_stress_range(path, 1, 1), (1.0, 2.0))


def test_temporary_res_element_ids_are_normalized_only_when_offset_is_clear():
    values = {
        0: np.zeros((2, 6)),
        1: np.ones((2, 6)),
    }
    shifted = _normalize_force_ids(values, {1, 2})
    assert set(shifted) == {1, 2}
    np.testing.assert_allclose(shifted[1], values[0])
    np.testing.assert_allclose(shifted[2], values[1])

    exact = _normalize_force_ids({1: values[0], 2: values[1]}, {1, 2})
    assert set(exact) == {1, 2}
