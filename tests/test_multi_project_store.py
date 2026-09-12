import copy

from opencae.controllers.project_sessions import ProjectStoreView
from opencae.model.entities.jobs import Job, JobStatus
from opencae.model.project import Project
from opencae.store.commands import UpdateFieldCommand
from opencae.store.multi_project_store import MultiProjectStore


def _rename(store, value):
    store.execute(
        f"Rename to {value}",
        UpdateFieldCommand(store.project.id, "name", store.project.name, value),
    )


def test_multi_project_store_keeps_document_history_independent():
    store = MultiProjectStore(Project(name="One"))
    _rename(store, "One edited")

    store.add_project(Project(name="Two"), reuse_placeholder=False)
    _rename(store, "Two edited")

    store.set_active_project(0)
    assert store.project.name == "One edited"
    store.undo()
    assert store.project.name == "One"

    store.set_active_project(1)
    assert store.project.name == "Two edited"
    store.undo()
    assert store.project.name == "Two"


def test_inactive_runtime_update_routes_to_owning_project_without_switching():
    first_job = Job(name="First Job")
    first = Project(name="One", jobs=[first_job])
    second = Project(name="Two")
    store = MultiProjectStore(first)
    store.add_project(second, reuse_placeholder=False)
    assert store.project is second

    store.update_runtime_fields(first_job.id, {"status": JobStatus.RUNNING})

    assert store.project is second
    first_live = store.projects[0].resolve(first_job.id)
    assert first_live.status is JobStatus.RUNNING


def test_project_store_view_pins_project_reads_to_entity_owner():
    first_job = Job(name="First Job")
    first = Project(name="One", jobs=[first_job])
    second = Project(name="Two")
    store = MultiProjectStore(first)
    store.add_project(second, reuse_placeholder=False)

    view = ProjectStoreView(store, first_job.id)

    assert store.project is second
    assert view.project is first
    assert view.project.resolve(first_job.id).name == "First Job"


def test_only_startup_placeholder_is_reused_for_first_open():
    store = MultiProjectStore()
    store.add_project(Project(name="First"))
    assert len(store.projects) == 1

    store.add_project(Project(name="Second"))
    assert [project.name for project in store.projects] == ["First", "Second"]


def test_closing_inactive_project_keeps_active_project_selected():
    first = Project(name="One")
    second = Project(name="Two")
    store = MultiProjectStore(first)
    store.add_project(second, reuse_placeholder=False)

    assert store.project is second
    assert store.close_project(0)
    assert store.project is second
    assert [project.name for project in store.projects] == ["Two"]


def test_closing_last_project_leaves_reusable_empty_placeholder():
    store = MultiProjectStore(Project(name="Only"))

    assert store.close_project(0)
    assert len(store.projects) == 1
    assert store.project.name == "Untitled"
    assert store.project.path is None
    assert store.is_placeholder_project(0)
    assert not store.close_project(0)

    store.add_project(Project(name="Replacement"))
    assert len(store.projects) == 1
    assert store.project.name == "Replacement"
    assert not store.is_placeholder_project(0)


def test_overlapping_document_identity_is_rejected():
    project = Project(name="Original")
    store = MultiProjectStore(project)

    duplicate = copy.deepcopy(project)
    duplicate.name = "Duplicate"
    duplicate.rebuild_index()

    try:
        store.add_project(duplicate, reuse_placeholder=False)
    except ValueError as exc:
        assert "shares persistent entity identities" in str(exc)
    else:
        raise AssertionError("duplicate persistent ids must be rejected")
