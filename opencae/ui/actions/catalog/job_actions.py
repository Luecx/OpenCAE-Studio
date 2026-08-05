"""Declares actions shared by the Jobs output area and context surfaces."""

from opencae.ui.actions.ids import A
from opencae.ui.actions.spec import ActionSpec
from opencae.ui.core.icon_factory import IconKind as I


def specs(controllers):
    jobs = controllers.jobs
    return (
        ActionSpec(A.JOB_STOP, "Stop", I.DELETE, jobs.stop_selected),
        ActionSpec(A.JOB_MONITOR, "Monitor", I.RESULTS, jobs.monitor_selected),
        ActionSpec(
            A.JOB_OPEN_RESULTS,
            "Open in Results",
            I.RESULTS,
            jobs.open_selected_results,
        ),
    )
