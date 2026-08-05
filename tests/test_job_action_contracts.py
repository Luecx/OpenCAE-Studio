"""Regression coverage for JobManager action bindings."""

from types import SimpleNamespace


def test_job_manager_exposes_action_handlers():
    from opencae.controllers.job_manager import JobManager

    for name in (
        "stop_selected",
        "open_selected_monitor",
        "open_selected_results",
    ):
        assert hasattr(JobManager, name), name


def test_job_action_catalog_uses_public_job_manager_methods():
    from opencae.ui.actions.catalog import job_actions

    calls = []
    jobs = SimpleNamespace(
        stop_selected=lambda: calls.append("stop"),
        open_selected_monitor=lambda: calls.append("monitor"),
        open_selected_results=lambda: calls.append("results"),
    )

    specs = job_actions.specs(SimpleNamespace(jobs=jobs))

    assert len(specs) == 3
    for spec in specs:
        spec.handler()
    assert calls == ["stop", "monitor", "results"]
