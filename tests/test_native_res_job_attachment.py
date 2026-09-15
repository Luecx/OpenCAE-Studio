"""Regression coverage for selecting native FEMaster RES after a solver run."""

from pathlib import Path
from types import SimpleNamespace

from opencae.controllers import job_manager_analysis
from opencae.model.entities.jobs import Job, JobStatus


class _Signal:
    def emit(self, *_args):
        return None


class _Project:
    def __init__(self, job):
        self.job = job

    def try_resolve(self, reference):
        identifier = getattr(reference, "entity_id", reference)
        return self.job if str(identifier) == self.job.id else None


class _Adapter:
    @staticmethod
    def result_candidates(output_base: Path):
        return [
            output_base.with_suffix(".res"),
            output_base.with_suffix(".frd"),
        ]


def test_finish_analysis_attaches_native_res_before_frd(tmp_path, monkeypatch):
    """A successful FEMaster job must not discard an available native RES."""
    output_base = tmp_path / "results"
    output_base.with_suffix(".res").write_text("LC 1\n", encoding="utf-8")
    output_base.with_suffix(".frd").write_text("FRD\n", encoding="utf-8")

    job = Job(name="Job-1", status=JobStatus.RUNNING)
    project = _Project(job)
    selected = []

    manager = SimpleNamespace(
        _runners={job.id: object()},
        store=SimpleNamespace(project=project),
        progress_changed=_Signal(),
        parent=SimpleNamespace(refresh_action_states=lambda: None),
        _replace_job=lambda candidate, _message: setattr(project, "job", candidate),
        _finish_analysis_runtime=lambda *_args: None,
    )
    monkeypatch.setattr(
        job_manager_analysis,
        "_attach_solver_result",
        lambda _manager, _job_id, source: selected.append(Path(source)),
    )

    job_manager_analysis.finish_analysis(
        manager,
        job.id,
        _Adapter(),
        output_base,
        0,
    )

    assert selected == [output_base.with_suffix(".res")]
    assert project.job.status is JobStatus.COMPLETED
