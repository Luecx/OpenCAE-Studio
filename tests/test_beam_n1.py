"""Regression coverage for the authoritative BeamSection n1 direction."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from opencae.model.entities.sections import BeamSection
from opencae.persistence.migrations.v25_to_v26 import migrate_v25_to_v26
from opencae.results.beam_physical_model import BeamOccurrence
from opencae.solvers.femaster_dsl.emitters.sections import write_section


class _Writer:
    def __init__(self):
        self.calls = []

    def command(self, name, data, *, flags, keywords, record_key):
        self.calls.append((name, tuple(data), dict(keywords)))


class _Context:
    def resolve(self, ref):
        return SimpleNamespace(name={"material": "Steel", "profile": "Rect"}[ref])

    @staticmethod
    def solver_name(_entity, name):
        return name


def test_beam_section_n1_is_validated_and_kept_as_authored_direction():
    section = BeamSection(name="Beam", n1=(1, 2, 3))
    assert section.n1 == (1.0, 2.0, 3.0)

    with pytest.raises(ValueError, match="non-zero"):
        BeamSection(name="Zero", n1=(0.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="finite"):
        BeamSection(name="NaN", n1=(float("nan"), 1.0, 0.0))


def test_schema_25_beam_direction_migrates_losslessly_to_n1():
    legacy_direction = {"__tuple__": [0.25, 0.5, 0.75]}
    source = {
        "format": "opencae-project",
        "schema_version": 25,
        "project": {
            "__type__": "project",
            "sections": [
                {
                    "__type__": "beam_section",
                    "name": "Beam",
                    "direction": legacy_direction,
                }
            ],
        },
    }

    migrated = migrate_v25_to_v26(source)
    section = migrated["project"]["sections"][0]

    assert migrated["schema_version"] == 26
    assert section["n1"] == legacy_direction
    assert "direction" not in section
    assert "direction" in source["project"]["sections"][0]


def test_femaster_beam_section_exports_n1_in_part_coordinates_without_instance():
    writer = _Writer()
    section = BeamSection(
        name="Beam",
        material_ref="material",
        profile_ref="profile",
        n1=(0.0, 0.0, 2.0),
    )

    write_section(section, "ESET", None, writer, _Context())

    name, data, keywords = writer.calls[-1]
    assert name == "BEAMSECTION"
    np.testing.assert_allclose(data[0], (0.0, 0.0, 2.0))
    assert keywords["ELSET"] == "ESET"
    assert keywords["MATERIAL"] == "Steel"
    assert keywords["PROFILE"] == "Rect"


def test_femaster_beam_section_rotates_n1_with_assembly_instance():
    writer = _Writer()
    section = BeamSection(
        name="Beam",
        material_ref="material",
        profile_ref="profile",
        n1=(1.0, 0.0, 0.0),
    )
    instance = SimpleNamespace(rotation=(0.0, 0.0, 90.0))

    write_section(section, "ESET", None, writer, _Context(), instance=instance)

    np.testing.assert_allclose(writer.calls[-1][1][0], (0.0, 1.0, 0.0), atol=1.0e-12)


def test_beam_occurrence_direction_compatibility_is_backed_only_by_n1():
    occurrence = BeamOccurrence(
        solver_element_id=1,
        part_id="part",
        instance_id="instance",
        source_element_id=7,
        connectivity=(1, 2),
        n1=(0.0, 0.0, 1.0),
        section=SimpleNamespace(),
        profile=SimpleNamespace(),
    )

    assert occurrence.n1 == (0.0, 0.0, 1.0)
    assert occurrence.direction == occurrence.n1
