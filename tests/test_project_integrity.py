"""Regression tests for transactional edits, references, validation and persistence."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from opencae.model.core import EntityRef
from opencae.model.entities.assembly import Instance
from opencae.model.entities.parts import Part
from opencae.model.entities.resources import Material
from opencae.model.project import Project
from opencae.model.validation import validate_project
from opencae.persistence.project_codec import (
    CURRENT_SCHEMA_VERSION,
    project_from_dict,
    project_to_dict,
)
from opencae.persistence.project_io import save_project
from opencae.store.commands import (
    CompositeCommand,
    ProjectCommand,
    UpdateFieldCommand,
)


class FailAfterMutation(ProjectCommand):
    """Test command that deliberately leaves a partial mutation before raising."""

    def apply(self, project):
        project.name = "BROKEN"
        raise RuntimeError("intentional apply failure")

    def undo(self, project):
        project.name = "Untitled"
        return project


class UndoFails(ProjectCommand):
    """Test command whose forward mutation succeeds but undo fails."""

    def apply(self, project):
        project.name = "APPLIED"
        return project

    def undo(self, project):
        project.name = "BROKEN_UNDO"
        raise RuntimeError("intentional undo failure")


class AlwaysFails(ProjectCommand):
    """Test command that fails without mutating its input."""

    def apply(self, project):
        raise RuntimeError("intentional composite failure")

    def undo(self, project):
        raise RuntimeError("not applied")


def test_analysis_validation_does_not_recurse_through_runtime_mesh_links(
    project_factory,
):
    """Starting analysis validation must not traverse runtime dataclass cycles."""
    data = project_factory(include_constraints=False)
    errors = validate_project(data["project"], analysis=data["analysis"])
    assert isinstance(errors, list)
    assert not errors


def test_entity_reference_assignment_rejects_foreign_project_objects():
    """A bound relationship cannot cache an Entity owned by another Project."""
    part_a = Part(name="A")
    project_a = Project(name="A", parts=[part_a])
    part_b = Part(name="B")
    instance = Instance(name="B-1", part_ref=EntityRef.of(part_b, "Part"))
    project_b = Project(name="B", parts=[part_b])
    project_b.assembly.instances.append(instance)
    project_b.rebuild_index(strict=True)

    with pytest.raises(ValueError, match="does not belong"):
        instance.part = part_a

    assert instance.part is part_b
    assert project_a.resolve(part_a.id) is part_a


def test_entity_reference_assignment_rejects_wrong_entity_type():
    """Descriptor assignment enforces the declared relationship type."""
    part = Part(name="P")
    instance = Instance(name="P-1", part_ref=EntityRef.of(part, "Part"))
    project = Project(name="P", parts=[part])
    project.assembly.instances.append(instance)
    material = Material(name="Steel")
    project.materials.append(material)
    project.rebuild_index(strict=True)

    with pytest.raises(TypeError, match="expects Part"):
        instance.part = material


def test_project_resolution_enforces_entity_ref_expected_type():
    """Expected-type metadata is enforced by the central ProjectIndex."""
    material = Material(name="Steel")
    project = Project(name="P", materials=[material])

    wrong = EntityRef(material.id, "Part")
    with pytest.raises(TypeError, match="expected Part"):
        project.resolve(wrong)
    assert project.try_resolve(wrong) is None


def test_entity_ref_of_rejects_display_names_and_raw_ids():
    """Public relationship construction accepts objects rather than strings."""
    with pytest.raises(TypeError, match="expects an Entity"):
        EntityRef.of("Part-1", "Part")


def test_store_execute_rolls_back_partial_mutation(project_factory):
    """A failed command leaves the Project and history exactly pre-attempt."""
    pytest.importorskip("PyQt6")
    from opencae.store.project_store import ProjectStore

    project = project_factory(include_constraints=False)["project"]
    before = project.name
    store = ProjectStore(project)

    with pytest.raises(RuntimeError, match="intentional apply failure"):
        store.execute("Broken", FailAfterMutation())

    assert store.project.name == before
    assert store._undo == []
    assert store._redo == []
    store.project.ensure_references(strict=True)


def test_composite_command_rolls_back_successful_children(project_factory):
    """CompositeCommand is atomic even when a later child fails."""
    project = project_factory(include_constraints=False)["project"]
    original = project.name
    command = CompositeCommand(
        (
            UpdateFieldCommand(project.id, "name", original, "TEMPORARY"),
            AlwaysFails(),
        )
    )

    with pytest.raises(RuntimeError, match="intentional composite failure"):
        command.apply(project)

    assert project.name == original
    project.ensure_references(strict=True)


def test_failed_undo_keeps_history_and_forward_state(project_factory):
    """Undo history moves between stacks only after a successful mutation."""
    pytest.importorskip("PyQt6")
    from opencae.store.project_store import ProjectStore

    store = ProjectStore(project_factory(include_constraints=False)["project"])
    store.execute("Apply", UndoFails())
    assert store.project.name == "APPLIED"
    assert len(store._undo) == 1

    with pytest.raises(RuntimeError, match="intentional undo failure"):
        store.undo()

    assert store.project.name == "APPLIED"
    assert len(store._undo) == 1
    assert store._redo == []


def test_persistence_omits_runtime_path_and_uses_current_envelope(
    project_factory,
    tmp_path,
):
    """Filesystem location is runtime state and not part of the domain payload."""
    project = project_factory(include_constraints=False)["project"]
    project.path = tmp_path / "source.ocae"
    encoded = project_to_dict(project)

    assert encoded["schema_version"] == CURRENT_SCHEMA_VERSION
    assert encoded["format"] == "opencae-project"
    assert "path" not in encoded["project"]
    assert "schema_version" not in encoded["project"]


def test_persistence_rejects_unknown_model_fields(project_factory):
    """Schema drift cannot silently discard unrecognized persisted data."""
    encoded = project_to_dict(
        project_factory(include_constraints=False)["project"]
    )
    encoded["project"]["future_field"] = "must not disappear"

    with pytest.raises(ValueError, match="Unknown persisted field"):
        project_from_dict(encoded)


def test_persistence_rejects_previous_schema(project_factory):
    """Development persistence deliberately has no backwards compatibility."""
    encoded = project_to_dict(
        project_factory(include_constraints=False)["project"]
    )
    encoded["schema_version"] = CURRENT_SCHEMA_VERSION - 1

    with pytest.raises(ValueError, match="is not supported"):
        project_from_dict(encoded)


def test_failed_atomic_save_does_not_change_project_path(
    project_factory,
    tmp_path,
    monkeypatch,
):
    """A filesystem replacement failure cannot commit a new runtime path."""
    import opencae.persistence.project_io as project_io

    project = project_factory(include_constraints=False)["project"]
    original = tmp_path / "original.ocae"
    project.path = original
    target = tmp_path / "new.ocae"

    def fail_replace(_source, _target):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(project_io.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        save_project(project, target)

    assert project.path == original
    assert not target.exists()
    assert not list(tmp_path.glob(".new.ocae.*.tmp"))


def test_store_rejects_invalid_active_part(project_factory):
    """Active-part state cannot point at arbitrary or missing entities."""
    pytest.importorskip("PyQt6")
    from opencae.store.project_store import ProjectStore

    store = ProjectStore(project_factory(include_constraints=False)["project"])
    with pytest.raises(ValueError, match="does not exist"):
        store.set_active_part("entity_missing")


def test_duplicate_id_insert_rolls_back_without_graph_damage(project_factory):
    """Global duplicate IDs are rejected before they become live ownership."""
    pytest.importorskip("PyQt6")
    from opencae.store.project_store import ProjectStore

    data = project_factory(include_constraints=False)
    store = ProjectStore(data["project"])
    duplicate = deepcopy(data["part"])

    with pytest.raises(ValueError, match="already exists"):
        store.add_entity(
            "Duplicate",
            store.project.id,
            "parts",
            duplicate,
        )

    assert len(store.project.parts) == 1
    assert store.project.parts[0].id == data["part"].id
    store.project.ensure_references(strict=True)
