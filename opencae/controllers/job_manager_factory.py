"""Creates Job records and filesystem locations for JobManager workflows."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from opencae.model.core import EntityRef
from opencae.model.entities.jobs import Job, JobSourceKind, JobStatus
from opencae.model.naming import next_name_from_names


def utc_now() -> str:
    """Return the current UTC timestamp in a persistence-friendly ISO format."""
    return datetime.now(timezone.utc).isoformat()


def job_directory(project, source_name: str) -> Path:
    """Return the next unused job directory for ``source_name``."""
    root = (
        project.path.parent / f"{project.path.stem}_data"
        if project.path
        else Path.cwd() / ".opencae"
    )
    name = next_name_from_names(
        f"{source_name} Job",
        [job.name for job in project.jobs],
    )
    directory = root / "jobs" / name.replace(" ", "-")
    counter = 2
    while directory.exists():
        directory = root / "jobs" / f"{name.replace(' ', '-')}-{counter}"
        counter += 1
    return directory


def create_job(
    project,
    source,
    source_kind: JobSourceKind | str,
    solver: str,
    directory: Path,
) -> Job:
    """Create a prepared Job without mutating the project collection."""
    directory.mkdir(parents=True, exist_ok=True)
    name = next_name_from_names(
        f"{source.name} Job",
        [job.name for job in project.jobs],
    )
    job = Job(
        name=name,
        source_ref=EntityRef.of(source, type(source).__name__),
        source_kind=JobSourceKind.coerce(source_kind),
        solver=str(solver),
        status=JobStatus.PREPARED,
        created_at=utc_now(),
    )
    job.directory = str(directory)
    job.output_file = str(directory / "output.log")
    return job
