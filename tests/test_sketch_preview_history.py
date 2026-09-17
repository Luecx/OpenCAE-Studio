"""Preview candidates must represent the real Part feature history without aliasing it."""

from opencae.model.entities.geometry import SketchFeature
from opencae.model.entities.parts import Part
from opencae.ui.other.sketcher.preview import build_preview_part


def test_preview_candidate_appends_new_feature_without_mutating_base_part():
    base_feature = SketchFeature(name="Base", mode="Extrusion", depth=4.0)
    base = Part(name="Bracket", geometry=[base_feature])
    new_feature = SketchFeature(
        name="Pocket",
        mode="Extrusion",
        operation="Cut",
        depth=2.0,
    )

    candidate = build_preview_part(base, new_feature)

    assert candidate.id != base.id
    assert [feature.id for feature in candidate.geometry] == [
        base_feature.id,
        new_feature.id,
    ]
    assert candidate.geometry[1] is not new_feature
    assert candidate.geometry[0] is not base_feature
    assert len(base.geometry) == 1


def test_preview_candidate_replaces_matching_feature_and_keeps_downstream_history():
    first = SketchFeature(name="Pad", mode="Extrusion", depth=4.0)
    target = SketchFeature(
        name="Pocket",
        mode="Extrusion",
        operation="Cut",
        depth=2.0,
    )
    downstream = SketchFeature(
        name="Boss",
        mode="Extrusion",
        operation="Add",
        depth=3.0,
    )
    base = Part(name="Bracket", geometry=[first, target, downstream])
    edited = SketchFeature(
        name=target.name,
        id=target.id,
        mode="Revolve",
        operation="Cut",
        angle_degrees=180.0,
    )

    candidate = build_preview_part(base, edited)

    assert candidate.id != base.id
    assert len(candidate.geometry) == 3
    assert [feature.id for feature in candidate.geometry] == [
        first.id,
        target.id,
        downstream.id,
    ]
    assert candidate.geometry[1].mode == "Revolve"
    assert candidate.geometry[1].angle_degrees == 180.0
    assert candidate.geometry[2].operation == "Add"
    assert base.geometry[1].mode == "Extrusion"
