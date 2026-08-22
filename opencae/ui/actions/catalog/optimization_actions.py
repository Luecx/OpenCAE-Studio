"""Declares actions exposed by the Studies ribbon and project tree."""

from opencae.ui.actions.ids import A
from opencae.ui.actions.spec import ActionSpec
from opencae.ui.core.icon_factory import IconKind as I


def specs(controllers):
    studies = controllers.optimization
    return (
        ActionSpec(
            A.STUDY_NEW_TOPOLOGY,
            "Topology",
            I.TOPOLOGY,
            studies.new_topology,
            status_tip="Create a Topology Optimization Study",
        ),
        ActionSpec(
            A.STUDY_EDIT,
            "Edit Study",
            I.EDIT,
            studies.edit_active_study,
        ),
        ActionSpec(A.OPT_RESPONSE, "Response", I.FIELD, studies.response),
        ActionSpec(A.OPT_OBJECTIVE, "Objective", I.CONTOUR, studies.objective),
        ActionSpec(A.OPT_CONSTRAINT, "Constraint", I.CONSTRAINT, studies.constraint),
        ActionSpec(A.OPT_FILTER, "Filters", I.FILTER, studies.filter_settings),
        ActionSpec(A.OPT_SYMMETRY, "Symmetry", I.SYMMETRY_SUPPORT, studies.symmetry),
        ActionSpec(A.OPT_CONTROLS, "Controls", I.SETTINGS, studies.controls),
        ActionSpec(A.STUDY_VALIDATE, "Validate", I.VALIDATE, studies.validate),
        ActionSpec(A.STUDY_RUN, "Run Study", I.RUN, studies.run_active),
        ActionSpec(A.OPT_PREVIOUS, "Previous", I.PREVIOUS_FRAME, studies.previous_iteration),
        ActionSpec(A.OPT_NEXT, "Next", I.NEXT_FRAME, studies.next_iteration),
        ActionSpec(A.OPT_THRESHOLD, "Threshold", I.THRESHOLD, studies.threshold),
    )
