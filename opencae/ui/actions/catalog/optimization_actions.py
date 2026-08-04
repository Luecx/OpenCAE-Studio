"""Declares actions exposed by the Optimization ribbon and project tree."""

from opencae.ui.actions.ids import A
from opencae.ui.actions.spec import ActionSpec
from opencae.ui.core.icon_factory import IconKind as I


def specs(controllers):
    """Return action specifications bound to the optimization controller."""

    optimization = controllers.optimization
    return (
        ActionSpec(
            A.OPT_NEW,
            "Topology",
            I.PART,
            optimization.new_topology,
            status_tip="Create or edit a topology optimization",
        ),
        ActionSpec(
            A.OPT_RESPONSE,
            "Response",
            I.FIELD,
            optimization.response,
            status_tip="Create a topology response",
        ),
        ActionSpec(
            A.OPT_OBJECTIVE,
            "Objective",
            I.CONTOUR,
            optimization.objective,
            status_tip="Select the optimization objective",
        ),
        ActionSpec(
            A.OPT_CONSTRAINT,
            "Constraint",
            I.CONSTRAINT,
            optimization.constraint,
            status_tip="Create a resource constraint",
        ),
        ActionSpec(
            A.OPT_FILTER,
            "Filters",
            I.RANGE,
            optimization.filter_settings,
            status_tip=(
                "Configure density/constraint and sensitivity filter radii"
            ),
        ),
        ActionSpec(
            A.OPT_SYMMETRY,
            "Symmetry",
            I.CSYS,
            optimization.symmetry,
            status_tip="Create planar or rotational topology symmetry",
        ),
        ActionSpec(
            A.OPT_CONTROLS,
            "Controls",
            I.SETTINGS,
            optimization.controls,
            status_tip="Configure OC and iteration controls",
        ),
        ActionSpec(
            A.OPT_VALIDATE,
            "Validate",
            I.VALIDATE,
            optimization.validate,
            status_tip="Validate topology setup and build sparse operators",
        ),
        ActionSpec(
            A.OPT_RUN,
            "Run Optimization",
            I.RUN,
            optimization.run,
            status_tip="Run FEMaster topology iterations",
        ),
        ActionSpec(
            A.OPT_STOP,
            "Stop",
            I.DELETE,
            optimization.stop,
            status_tip="Stop the active topology run",
        ),
        ActionSpec(
            A.OPT_PREVIOUS,
            "Previous",
            I.PREVIOUS_FRAME,
            optimization.previous_iteration,
        ),
        ActionSpec(
            A.OPT_NEXT,
            "Next",
            I.NEXT_FRAME,
            optimization.next_iteration,
        ),
        ActionSpec(
            A.OPT_THRESHOLD,
            "Threshold",
            I.RANGE,
            optimization.threshold,
        ),
    )
