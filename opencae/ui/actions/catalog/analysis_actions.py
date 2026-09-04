"""Declares shared Step and Analysis actions."""

from opencae.ui.actions.ids import A
from opencae.ui.actions.spec import ActionSpec
from opencae.ui.core.icon_factory import IconKind as I


def specs(c):
    return (
        ActionSpec(A.STEP_LINEAR, "Linear Static", I.STEP_LINEAR, lambda: c.analysis.create_step("Linear Static")),
        ActionSpec(A.STEP_NONLINEAR, "Nonlinear", I.STEP_NONLINEAR, lambda: c.analysis.create_step("Nonlinear Static")),
        ActionSpec(A.STEP_MODAL, "Modal", I.STEP_MODAL, lambda: c.analysis.create_step("Eigenfrequency")),
        ActionSpec(A.STEP_BUCKLING, "Buckling", I.STEP_BUCKLING, lambda: c.analysis.create_step("Linear Buckling")),
        ActionSpec(A.STEP_TRANSIENT, "Transient", I.STEP_TRANSIENT, lambda: c.analysis.create_step("Transient")),
        ActionSpec(A.REORDER_STEPS, "Reorder", I.REORDER, c.analysis.reorder_steps),
        ActionSpec(A.STEP_MATRIX, "Collectors", I.MATRIX, c.analysis.manage_collectors),
        ActionSpec(A.ANALYSIS_NEW, "New Analysis", I.NEW_ANALYSIS, c.analysis.new_analysis),
        ActionSpec(A.ANALYSIS_EDIT, "Edit Analysis", I.EDIT, c.analysis.edit_active_analysis),
        ActionSpec(
            A.DECK_FORMAT_MANAGER,
            "Input Deck Formats…",
            I.DECK,
            c.solver.format_manager,
        ),
        ActionSpec(A.VALIDATE, "Validate", I.VALIDATE, c.analysis.validate_active, "F7"),
        ActionSpec(A.PREVIEW_DECK, "Preview Deck", I.PREVIEW_DECK, c.solver.preview),
        ActionSpec(A.WRITE_DECK, "Write Deck", I.WRITE_DECK, c.solver.write),
        ActionSpec(A.ANALYSIS_RUN, "Run Analysis", I.RUN, c.analysis.run_active, "F5"),
    )
