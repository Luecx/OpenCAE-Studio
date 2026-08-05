"""Selector-first ribbon page for executable Analysis definitions."""

from opencae.ui.actions.ids import A
from opencae.ui.core.widgets import EntitySelectorBar


def create(actions, store, controllers):
    """Build the Analysis page with selector and shared central actions."""

    return EntitySelectorBar(
        "Analysis",
        store,
        actions,
        entities_provider=lambda: store.project.analyses,
        active_id_provider=lambda: controllers.analysis.active_analysis_id,
        activate=controllers.analysis.set_active_analysis,
        action_ids=(
            A.ANALYSIS_NEW,
            A.ANALYSIS_EDIT,
            A.DELETE_SELECTED,
            A.SOLVER_SETTINGS,
            A.VALIDATE,
            A.PREVIEW_DECK,
            A.WRITE_DECK,
            A.ANALYSIS_RUN,
        ),
    )
