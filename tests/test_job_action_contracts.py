"""Regression coverage for JobManager action bindings."""

from types import SimpleNamespace


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
        spec.callback()
    assert calls == ["stop", "monitor", "results"]
