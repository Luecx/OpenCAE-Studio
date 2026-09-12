"""Architecture contracts for bounded persistence migration and identity ownership."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "opencae"


def test_historical_persistence_implementations_are_removed():
    """Persistence keeps one codec plus the dedicated versioned migration package."""
    forbidden = (
        "persistence/legacy",
        "persistence/migrations.py",
        "persistence/mesh_definition_migration.py",
        "model/entities/project_migrations.py",
    )
    for relative in forbidden:
        assert not (ROOT / relative).exists()


def test_obsolete_identity_and_region_runtime_paths_are_removed():
    """Only the canonical EntityRef and RegionDefinition models remain live."""
    forbidden = (
        "model/core/region_member.py",
        "model/core/target_options.py",
        "model/entities/constraints/reference.py",
        "solvers/femaster_dsl/emitters/target_resolution.py",
        "controllers/region_dialog_session.py",
        "ui/core/widgets/selection_members.py",
        "store/json_patch.py",
    )
    for relative in forbidden:
        assert not (ROOT / relative).exists()


def test_entity_ref_has_no_name_fallback_identity():
    """EntityRef persistence is stable-ID-only."""
    text = (ROOT / "model/core/reference.py").read_text(encoding="utf-8")
    assert "legacy_name" not in text
    assert "hasattr(entity, \"id\")" not in text
    assert "isinstance(entity, Entity)" in text


def test_project_has_no_schema_or_legacy_collection_state():
    """File-format version and former optimization aliases stay outside Project."""
    text = (ROOT / "model/entities/project.py").read_text(encoding="utf-8")
    assert "schema_version:" not in text
    assert "optimizations:" not in text
    assert 'metadata={"serialize": False}' in text


def test_project_codec_uses_dedicated_bounded_migration_dispatch():
    """Schema migration is explicit, bounded and kept outside the domain model."""
    codec = (ROOT / "persistence/project_codec.py").read_text(encoding="utf-8")
    migrations = (ROOT / "persistence/migrations/__init__.py").read_text(
        encoding="utf-8"
    )
    assert "CURRENT_SCHEMA_VERSION" in codec
    assert "MINIMUM_SCHEMA_VERSION" in codec
    assert "PROJECT_FORMAT" in codec
    assert "from .migrations import migrate_project_data" in codec
    assert "migrate_project_data(data, version, CURRENT_SCHEMA_VERSION)" in codec
    assert "v23_to_v24" not in codec
    assert "def migrate_project_data" in migrations


def test_reference_validation_has_one_authoritative_walker():
    """Workflow validation must reuse the core reference validator."""
    validation = (ROOT / "model/validation.py").read_text(encoding="utf-8")
    binding = (ROOT / "model/core/reference_binding.py").read_text(
        encoding="utf-8"
    )
    assert "def _reference_errors" not in validation
    assert "project.ensure_references" in validation
    assert "active_values" in binding


def test_project_io_uses_atomic_replacement():
    """Project writes use a same-directory temporary file and os.replace."""
    text = (ROOT / "persistence/project_io.py").read_text(encoding="utf-8")
    assert "tempfile.mkstemp" in text
    assert "os.fsync" in text
    assert "os.replace" in text
