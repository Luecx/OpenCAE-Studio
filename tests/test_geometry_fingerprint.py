"""Regression coverage for geometry cache fingerprints on live project graphs."""

from opencae.geometry.fingerprint import part_fingerprint
from opencae.model.entities.geometry import ImportedStepFeature
from opencae.model.entities.parts import Part
from opencae.model.project import Project


def test_bound_geometry_feature_fingerprint_is_acyclic_and_stable():
    """Fingerprint a feature after ProjectIndex installs its runtime backreference."""
    feature = ImportedStepFeature(
        name="Import-1",
        source_file="bracket.step",
    )
    part = Part(name="Bracket", geometry=[feature])
    project = Project(name="Fingerprint test", parts=[part])

    # This is the production state that made dataclasses.asdict recurse through
    # feature._project -> project.parts -> part.geometry -> feature indefinitely.
    assert feature.project is project

    first = part_fingerprint(part)
    second = part_fingerprint(part)

    assert first == second
    assert len(first) == 64


def test_geometry_fingerprint_changes_when_persisted_feature_state_changes():
    """Keep cache invalidation sensitive to geometry-defining feature edits."""
    feature = ImportedStepFeature(
        name="Import-1",
        source_file="first.step",
    )
    part = Part(name="Bracket", geometry=[feature])
    Project(name="Fingerprint test", parts=[part])

    before = part_fingerprint(part)
    feature.source_file = "second.step"
    after = part_fingerprint(part)

    assert before != after
