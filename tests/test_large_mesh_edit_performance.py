"""Regression contracts for edits on Projects containing very large FE meshes."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

from opencae.controllers.part.context import PartContext
from opencae.model.core import clone_entity_graph
from opencae.model.entities.analysis import AnalysisStep
from opencae.model.entities.mesh import DefaultSeed, MeshState
from opencae.store.commands import (
    CompositeCommand,
    UpdateFieldCommand,
    make_replace_command,
)
from opencae.store.owned_collection_insert import OwnedCollectionInsertCommand
from opencae.store.owned_field_swap import OwnedFieldSwapCommand
from opencae.store.project_store import ProjectStore


class _IterationProbe(list):
    """List recording bulk scans while preserving normal list behavior."""

    def __init__(self, values):
        super().__init__(values)
        self.iterations = 0

    def __iter__(self):
        self.iterations += 1
        return super().__iter__()


def _install_mesh_probes(part):
    """Replace representative large numeric mesh arrays with scan counters."""
    probes = [
        _IterationProbe(part.mesh.nodes.ids),
        _IterationProbe(part.mesh.nodes.coordinates),
    ]
    part.mesh.nodes.ids = probes[0]
    part.mesh.nodes.coordinates = probes[1]
    for block in part.mesh.element_blocks:
        ids = _IterationProbe(block.ids)
        connectivity = _IterationProbe(block.connectivity)
        block.ids = ids
        block.connectivity = connectivity
        probes.extend((ids, connectivity))
    return probes


def _assert_no_bulk_scan(probes):
    assert all(probe.iterations == 0 for probe in probes)


def test_builtin_undo_history_never_snapshots_the_complete_project(
    project_factory,
    monkeypatch,
):
    """Normal execute/undo/redo must use command deltas, not Project deepcopy."""
    import opencae.store.project_store as project_store_module

    store = ProjectStore(project_factory(include_constraints=False)["project"])

    def reject_project_snapshot(_value):
        raise AssertionError("ProjectStore attempted a full document deepcopy")

    monkeypatch.setattr(project_store_module, "deepcopy", reject_project_snapshot)
    step = AnalysisStep(name="LARGE_MESH_EDIT", step_type="Linear Static")

    store.add_entity("Created step", store.project.id, "steps", step)
    assert store.project.try_resolve(step.id) is not None
    store.undo()
    assert store.project.try_resolve(step.id) is None
    store.redo()
    assert store.project.try_resolve(step.id) is not None


def test_entity_deepcopy_does_not_follow_project_backreference(project_factory):
    """Copying a small bound Entity must not copy or scan its owning Part mesh."""
    project = project_factory(include_constraints=False)["project"]
    part = project.parts[0]
    seed = DefaultSeed(name="Default Seed", size=1.0)
    part.mesh.seeds.append(seed)
    project.rebuild_index(strict=True)
    bound_seed = project.resolve(seed.id)
    probes = _install_mesh_probes(part)

    detached = deepcopy(bound_seed)

    assert detached.id == bound_seed.id
    assert detached.project is None
    _assert_no_bulk_scan(probes)


def test_new_step_does_not_walk_numeric_mesh_payload(project_factory):
    """Issue #39: creating a Step must be independent of mesh element count."""
    store = ProjectStore(project_factory(include_constraints=False)["project"])
    probes = _install_mesh_probes(store.active_part())
    step = AnalysisStep(name="SECOND_STEP", step_type="Linear Static")

    store.add_entity("Created second step", store.project.id, "steps", step)

    assert store.project.resolve(step.id).name == "SECOND_STEP"
    _assert_no_bulk_scan(probes)


def test_default_seed_edit_does_not_walk_numeric_mesh_payload(project_factory):
    """Issue #39: changing seed metadata must not traverse generated connectivity."""
    project = project_factory(include_constraints=False)["project"]
    part = project.parts[0]
    seed = DefaultSeed(name="Default Seed", size=1.0)
    part.mesh.seeds.append(seed)
    project.rebuild_index(strict=True)
    store = ProjectStore(project)
    part = store.active_part()
    seed = next(item for item in part.mesh.seeds if item.id == seed.id)
    probes = _install_mesh_probes(part)

    replacement = DefaultSeed(
        id=seed.id,
        name=seed.name,
        size=0.5,
        metadata=dict(seed.metadata),
    )
    command = CompositeCommand(
        (
            make_replace_command(store.project, part.id, "mesh.seeds", replacement),
            UpdateFieldCommand(
                part.id,
                "mesh.status",
                part.mesh.status,
                "Outdated",
            ),
        )
    )

    store.execute("Updated default seed", command)

    updated = store.project.resolve(seed.id)
    assert updated.size == 0.5
    _assert_no_bulk_scan(probes)


def test_reference_free_mesh_settings_edit_keeps_existing_project_index(
    project_factory,
):
    """Reference-free nested settings updates should not invalidate ProjectIndex."""
    store = ProjectStore(project_factory(include_constraints=False)["project"])
    part = store.active_part()
    index_before = store.project.index
    before = part.mesh.settings
    after = replace(before, num_threads=8)

    store.execute(
        "Updated mesh settings",
        UpdateFieldCommand(part.id, "mesh.settings", before, after),
    )

    assert store.project.index is index_before
    assert part.mesh.settings.num_threads == 8
    store.undo()
    assert store.project.index is index_before
    assert part.mesh.settings.num_threads == before.num_threads


def test_geometry_candidate_shares_large_payload_read_only(project_factory):
    """Geometry edits copy history/settings only and never iterate generated FE arrays."""
    store = ProjectStore(project_factory(include_constraints=False)["project"])
    part = store.active_part()
    probes = _install_mesh_probes(part)
    context = PartContext(store, None)

    candidate = context.geometry_candidate(part)

    assert candidate is not part
    assert candidate.geometry is not part.geometry
    assert candidate.geometry_settings is not part.geometry_settings
    assert candidate.mesh is not part.mesh
    assert candidate.mesh.nodes is part.mesh.nodes
    assert candidate.mesh.element_blocks is part.mesh.element_blocks
    _assert_no_bulk_scan(probes)


def test_mesh_generation_candidate_excludes_existing_generated_payload(project_factory):
    """A meshing worker receives configuration, not a copy of the mesh it replaces."""
    store = ProjectStore(project_factory(include_constraints=False)["project"])
    part = store.active_part()
    probes = _install_mesh_probes(part)
    context = PartContext(store, None)

    candidate = context.mesh_generation_candidate(part)

    assert candidate.mesh is not part.mesh
    assert candidate.mesh.nodes.ids == []
    assert candidate.mesh.nodes.coordinates == []
    assert candidate.mesh.element_blocks == []
    assert candidate.mesh.entity_nodes == {}
    assert candidate.mesh.entity_elements == {}
    assert candidate.mesh.seeds == part.mesh.seeds
    assert candidate.mesh.seeds is not part.mesh.seeds
    _assert_no_bulk_scan(probes)


def test_large_mesh_field_history_swaps_objects_without_copying(project_factory):
    """Generated mesh replacement keeps exactly one old and one new MeshState."""
    store = ProjectStore(project_factory(include_constraints=False)["project"])
    part = store.active_part()
    old_mesh = part.mesh
    probes = _install_mesh_probes(part)
    replacement = MeshState(
        settings=deepcopy(old_mesh.settings),
        seeds=deepcopy(old_mesh.seeds),
        status="Current",
        revision="replacement",
    )
    command = OwnedFieldSwapCommand(part.id, "mesh", replacement)

    store.execute("Replaced mesh", command)

    assert store.active_part().mesh is replacement
    assert command.replacement is old_mesh
    _assert_no_bulk_scan(probes)

    store.undo()
    assert store.active_part().mesh is old_mesh
    assert command.replacement is replacement
    _assert_no_bulk_scan(probes)

    store.redo()
    assert store.active_part().mesh is replacement
    assert command.replacement is old_mesh
    _assert_no_bulk_scan(probes)


def test_large_part_insert_transfers_exact_detached_object(project_factory):
    """Import/duplicate-style Part insertion does not recopy its generated mesh."""
    store = ProjectStore(project_factory(include_constraints=False)["project"])
    source = store.active_part()
    clone = clone_entity_graph(source)
    probes = _install_mesh_probes(clone)
    command = OwnedCollectionInsertCommand(
        store.project.id,
        "parts",
        clone,
        len(store.project.parts),
    )

    store.execute("Inserted large part", command)

    inserted = store.project.resolve(clone.id)
    assert inserted is clone
    assert command.entity is clone
    _assert_no_bulk_scan(probes)

    store.undo()
    assert store.project.try_resolve(clone.id) is None
    assert command.entity is clone
    _assert_no_bulk_scan(probes)

    store.redo()
    assert store.project.resolve(clone.id) is clone
    _assert_no_bulk_scan(probes)


def test_undo_retains_only_two_inactive_mesh_payloads(project_factory):
    """Repeated mesh replacement must not pin an unbounded mesh history in RAM."""
    store = ProjectStore(project_factory(include_constraints=False)["project"])
    part_id = store.active_part().id
    replacements = [
        MeshState(status="Current", revision=f"mesh-{index}")
        for index in range(1, 4)
    ]

    for replacement in replacements:
        store.execute(
            f"Generated {replacement.revision}",
            OwnedFieldSwapCommand(part_id, "mesh", replacement),
        )

    large_entries = [
        entry for entry in store._undo if entry.command.retains_large_payload()
    ]
    assert len(large_entries) == 2
    assert store.active_part().mesh is replacements[-1]

    store.undo()
    assert store.active_part().mesh is replacements[-2]
    store.undo()
    assert store.active_part().mesh is replacements[-3]
    assert store._undo == []
