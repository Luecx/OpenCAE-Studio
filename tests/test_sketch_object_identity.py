"""Persistence invariants for the object-native parametric sketch graph."""

from opencae.model.core import clone_entity_graph, decode_model, encode_model
from opencae.model.entities.geometry import (
    SketchConstraint,
    SketchDefinition,
    SketchFeature,
    SketchLine,
    SketchPoint,
)
from opencae.model.entities.parts import Part


def _sketched_part() -> Part:
    a = SketchPoint(x=0.0, y=0.0)
    b = SketchPoint(x=10.0, y=0.0)
    c = SketchPoint(x=10.0, y=5.0)
    d = SketchPoint(x=0.0, y=5.0)
    lines = (
        SketchLine(start=a, end=b),
        SketchLine(start=b, end=c),
        SketchLine(start=c, end=d),
        SketchLine(start=d, end=a),
    )
    sketch = SketchDefinition(
        points=[a, b, c, d],
        entities=list(lines),
        constraints=[SketchConstraint(kind="Horizontal", refs=(lines[0],))],
    )
    return Part(
        name="Sketched",
        geometry=[SketchFeature(name="Pad", sketch=sketch, depth=2.0)],
    )


def test_duplicate_part_may_reuse_local_sketch_ids_without_codec_collision():
    original = _sketched_part()
    duplicate = clone_entity_graph(original)

    original_sketch = original.geometry[0].sketch
    duplicate_sketch = duplicate.geometry[0].sketch
    assert duplicate.id != original.id
    assert duplicate.geometry[0].id != original.geometry[0].id
    assert duplicate_sketch.points[0].id == original_sketch.points[0].id
    assert duplicate_sketch.points[0] is not original_sketch.points[0]

    decoded_original, decoded_duplicate = decode_model(
        encode_model((original, duplicate))
    )
    for part in (decoded_original, decoded_duplicate):
        sketch = part.geometry[0].sketch
        assert sketch.entities[0].start is sketch.points[0]
        assert sketch.entities[0].end is sketch.points[1]
        assert sketch.constraints[0].refs[0] is sketch.entities[0]


def test_deep_object_relationships_are_aliases_not_repeated_payload_copies():
    part = _sketched_part()
    encoded = encode_model(part)
    sketch_payload = encoded["geometry"][0]["sketch"]

    line_payload = sketch_payload["entities"][0]
    assert set(line_payload["start"]) == {"__model_ref__"}
    assert set(line_payload["end"]) == {"__model_ref__"}
    constraint_ref = sketch_payload["constraints"][0]["refs"]["__tuple__"][0]
    assert set(constraint_ref) == {"__model_ref__"}
