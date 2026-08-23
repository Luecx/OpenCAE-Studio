"""Declare actions shared by the Jobs table and Job monitor workflow."""

from opencae.ui.actions.ids import A
from opencae.ui.actions.spec import ActionSpec
from opencae.ui.core.icon_factory import IconKind as I


def specs(controllers):
    """Return the canonical actions operating on JobManager's selected Job."""
    jobs = controllers.jobs
    return (
        ActionSpec(A.JOB_STOP, "Stop", I.DELETE, jobs.stop_selected),
        ActionSpec(
            A.JOB_MONITOR,
            "Open Monitor",
            I.JOB_MONITOR,
            jobs.open_selected_monitor,
        ),
        ActionSpec(
            A.JOB_OPEN_RESULTS,
            "Open in Results",
            I.RESULTS,
            jobs.open_selected_results,
        ),
    )
