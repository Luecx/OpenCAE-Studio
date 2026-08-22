"""Active Study selector, setup actions and execution ribbon page."""

from opencae.ui.actions.ids import A
from opencae.ui.core.widgets import EntitySelectorBar

from .ribbon_page import ResponsiveRibbonPage
from .specs import RibbonGroupSpec


class StudiesPage(ResponsiveRibbonPage):
    """Select and execute a Study while exposing type-specific setup actions."""

    def __init__(self, actions, store, controllers, parent=None):
        selector_bar = EntitySelectorBar(
            "Active Study",
            store,
            lambda: store.project.studies,
            lambda: controllers.studies.active_study_id,
            controllers.studies.set_active_study,
        )
        specs = (
            RibbonGroupSpec(
                "DEFINITION",
                (
                    A.STUDY_NEW_TOPOLOGY,
                    A.STUDY_EDIT,
                    A.DELETE_SELECTED,
                ),
            ),
            RibbonGroupSpec(
                "TOPOLOGY SETUP",
                (
                    A.OPT_RESPONSE,
                    A.OPT_OBJECTIVE,
                    A.OPT_CONSTRAINT,
                    A.OPT_FILTER,
                    A.OPT_SYMMETRY,
                    A.OPT_CONTROLS,
                ),
            ),
            RibbonGroupSpec(
                "STUDY",
                (
                    A.STUDY_VALIDATE,
                    A.STUDY_RUN,
                ),
            ),
        )
        super().__init__(
            specs,
            actions,
            leading_widgets=(selector_bar,),
            parent=parent,
        )
        self.selector_bar = selector_bar


def create(actions, store, controllers):
    return StudiesPage(actions, store, controllers)
