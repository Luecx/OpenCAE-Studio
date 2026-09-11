"""Active Analysis selector and execution ribbon page."""

from opencae.ui.actions.ids import A
from opencae.ui.core.widgets import EntitySelectorBar

from .ribbon_page import ResponsiveRibbonPage
from .specs import RibbonGroupSpec


class AnalysisPage(ResponsiveRibbonPage):
    """Select, edit, validate and start one Analysis definition."""

    def __init__(self, actions, store, controllers, parent=None):
        selector_bar = EntitySelectorBar(
            "Active Analysis",
            store,
            lambda: store.project.analyses,
            lambda: controllers.analysis.active_analysis_id,
            controllers.analysis.set_active_analysis,
        )
        specs = (
            RibbonGroupSpec(
                "DEFINITION",
                (
                    A.ANALYSIS_NEW,
                    A.ANALYSIS_EDIT,
                    A.DELETE_SELECTED,
                ),
            ),
            RibbonGroupSpec(
                "ANALYSIS",
                (
                    A.VALIDATE,
                    A.PREVIEW_DECK,
                    A.WRITE_DECK,
                    A.ANALYSIS_RUN,
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
    return AnalysisPage(actions, store, controllers)
