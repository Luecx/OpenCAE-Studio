"""Persists ResultSet entities and links them back to their producing Jobs."""

from __future__ import annotations

from copy import deepcopy

from opencae.model.core import EntityRef
from opencae.model.entities.jobs import Job, ResultSet


def persist_result(store, job_id: str, result: ResultSet) -> None:
    """Insert/update one ResultSet and make it the Job's active result link."""
    project = store.project
    previous = next(
        (
            item
            for item in project.results
            if item.job_ref and item.job_ref.entity_id == job_id
        ),
        None,
    )

    if previous is None:
        result_id = result.id
        store.add_entity(
            f"Added results for {result.name}",
            project.id,
            "results",
            result,
        )
    else:
        # Preserve ResultSet identity so existing tree selections and external
        # references survive reruns of the same Job.
        replacement = deepcopy(previous)
        replacement.name = result.name
        replacement.job_ref = result.job_ref
        replacement.source_file = result.source_file
        replacement.status = result.status
        replacement.fields = deepcopy(result.fields)
        replacement.metadata = deepcopy(result.metadata)
        result_id = replacement.id
        store.replace_entity(
            f"Updated results for {result.name}",
            project.id,
            "results",
            replacement,
        )

    current_job = store.project.try_resolve(job_id)
    current_result = store.project.try_resolve(result_id)
    if not isinstance(current_job, Job) or current_result is None:
        return

    candidate = deepcopy(current_job)
    candidate.result_refs = [EntityRef.of(current_result, "ResultSet")]
    store.replace_entity(
        f"Linked results to {current_job.name}",
        store.project.id,
        "jobs",
        candidate,
    )
