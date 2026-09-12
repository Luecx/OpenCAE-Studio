"""Behavioral coverage for canonical finite-domain model values."""

import pytest

from opencae.model.core import decode_model, encode_model
from opencae.model.entities.analysis import AnalysisStep, StepType
from opencae.model.entities.fields import (
    FieldDefinition,
    FieldInterpolation,
    FieldLocation,
    FieldSourceKind,
    FieldValueKind,
)
from opencae.model.entities.parts import Part, PartSourceKind


def test_step_type_normalizes_legacy_text_and_rejects_unknown_procedures():
    """Make StepType the mutation-boundary source of truth for procedures."""
    step = AnalysisStep(name="Transient", step_type="Linear Transient")
    assert step.step_type is StepType.TRANSIENT

    step.step_type = "eigenfrequency"
    assert step.step_type is StepType.EIGENFREQUENCY
    with pytest.raises(ValueError):
        step.step_type = "User-defined mystery procedure"


def test_part_source_kind_is_canonical_for_default_api_and_import_origins():
    """Keep Part origin values typed during construction and later mutation."""
    part = Part(name="Part")
    assert part.source_type is PartSourceKind.MANUAL

    part.source_type = "orphan mesh"
    assert part.source_type is PartSourceKind.ORPHAN_MESH
    with pytest.raises(ValueError):
        part.source_type = "Spreadsheet"


def test_field_finite_values_normalize_at_every_mutation_boundary():
    """Keep location, source, interpolation, and value shape canonical."""
    field = FieldDefinition(
        name="Temperature",
        location="nodal",
        source_type="tabular",
        interpolation="nearest",
        field_type="scalar",
    )
    assert field.location is FieldLocation.NODAL
    assert field.source_type is FieldSourceKind.TABULAR
    assert field.interpolation is FieldInterpolation.NEAREST
    assert field.field_type is FieldValueKind.SCALAR

    with pytest.raises(ValueError):
        field.location = "Everywhere-ish"


def test_finite_domain_enums_round_trip_as_stable_schema_text():
    """Persist readable values while restoring typed runtime state."""
    original = AnalysisStep(name="Static", step_type=StepType.LINEAR_STATIC)
    encoded = encode_model(original)
    assert encoded["step_type"] == "Linear Static"

    restored = decode_model(encoded)
    assert isinstance(restored, AnalysisStep)
    assert restored.step_type is StepType.LINEAR_STATIC
