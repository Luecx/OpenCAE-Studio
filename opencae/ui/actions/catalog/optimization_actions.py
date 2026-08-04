from opencae.ui.actions.ids import A
from opencae.ui.actions.spec import ActionSpec
from opencae.ui.core.icon_factory import IconKind as I


def specs(c):
    o = c.optimization
    return (
        ActionSpec(A.OPT_NEW, "Topology", I.PART, o.new_topology, status_tip="Create or edit a topology optimization"),
        ActionSpec(A.OPT_RESPONSE, "Response", I.FIELD, o.response, status_tip="Create a topology response"),
        ActionSpec(A.OPT_OBJECTIVE, "Objective", I.CONTOUR, o.objective, status_tip="Select the optimization objective"),
        ActionSpec(A.OPT_CONSTRAINT, "Constraint", I.CONSTRAINT, o.constraint, status_tip="Create a resource constraint"),
        ActionSpec(A.OPT_FILTER, "Filters", I.RANGE, o.filter_settings, status_tip="Configure density/constraint and sensitivity filter radii"),
        ActionSpec(A.OPT_SYMMETRY, "Symmetry", I.CSYS, o.symmetry, status_tip="Create planar or rotational topology symmetry"),
        ActionSpec(A.OPT_CONTROLS, "Controls", I.SETTINGS, o.controls, status_tip="Configure OC and iteration controls"),
        ActionSpec(A.OPT_VALIDATE, "Validate", I.VALIDATE, o.validate, status_tip="Validate topology setup and build sparse operators"),
        ActionSpec(A.OPT_RUN, "Run Optimization", I.RUN, o.run, status_tip="Run FEMaster topology iterations"),
        ActionSpec(A.OPT_STOP, "Stop", I.DELETE, o.stop, status_tip="Stop the active topology run"),
        ActionSpec(A.OPT_PREVIOUS, "Previous", I.PREVIOUS_FRAME, o.previous_iteration),
        ActionSpec(A.OPT_NEXT, "Next", I.NEXT_FRAME, o.next_iteration),
        ActionSpec(A.OPT_THRESHOLD, "Threshold", I.RANGE, o.threshold),
    )
