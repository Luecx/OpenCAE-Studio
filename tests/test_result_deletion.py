"""Regression coverage for referentially safe ResultSet deletion."""

from opencae.model.core import EntityRef
from opencae.model.entities.jobs import Job, ResultSet
from opencae.model.project import Project
from opencae.store.multi_project_store import MultiProjectStore


def _result_ids(job):
    return [reference.entity_id for reference in job.result_refs]


def test_delete_result_unlinks_jobs_atomically_and_undo_restores_links():
    project = Project(name="Result deletion")
    job = Job(name="Solver job")
    deleted = ResultSet(name="Deleted result")
    retained = ResultSet(name="Retained result")
    project.jobs.append(job)
    project.results.extend((deleted, retained))
    job.result_refs = [
        EntityRef.of(deleted, "ResultSet"),
        EntityRef.of(retained, "ResultSet"),
    ]
    project.ensure_references(strict=True)

    store = MultiProjectStore(project)
    store.delete_entity("Delete result", project.id, "results", deleted.id)

    assert [result.id for result in project.results] == [retained.id]
    assert _result_ids(job) == [retained.id]
    project.ensure_references(strict=True)

    store.undo()

    assert [result.id for result in project.results] == [deleted.id, retained.id]
    restored_job = project.resolve(job.id)
    assert _result_ids(restored_job) == [deleted.id, retained.id]
    project.ensure_references(strict=True)

    store.redo()

    assert [result.id for result in project.results] == [retained.id]
    assert _result_ids(project.resolve(job.id)) == [retained.id]
    project.ensure_references(strict=True)
