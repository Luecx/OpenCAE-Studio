"""Selector-first ribbon page for executable Studies."""

from opencae.ui.actions.ids import A
from opencae.ui.core.widgets import EntitySelectorBar


def create(actions, store, controllers):
    """Build the Studies page with topology setup and Run beside its selector."""

    return EntitySelectorBar(
        "Study",
        store,
        actions,
        entities_provider=lambda: store.project.studies,
        active_id_provider=lambda: controllers.studies.active_study_id,
        activate=controllers.studies.set_active_study,
        action_ids=(
            A.STUDY_NEW_TOPOLOGY,
            A.STUDY_EDIT,
            A.DELETE_SELECTED,
            A.OPT_RESPONSE,
            A.OPT_OBJECTIVE,
            A.OPT_CONSTRAINT,
            A.OPT_FILTER,
            A.OPT_SYMMETRY,
            A.OPT_CONTROLS,
            A.STUDY_VALIDATE,
            A.STUDY_RUN,
        ),
    )
