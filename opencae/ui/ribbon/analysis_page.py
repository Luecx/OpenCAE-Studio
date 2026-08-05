"""Active Analysis selector and execution ribbon page."""

from PyQt6.QtWidgets import QHBoxLayout, QWidget

from opencae.ui.actions.ids import A
from opencae.ui.core.widgets import EntitySelectorBar

from .ribbon_group import RibbonGroup
from .specs import RibbonGroupSpec


class AnalysisPage(QWidget):
    """Select, edit, validate and start one Analysis definition."""

    def __init__(self, actions, store, controllers, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 0, 0)
        layout.setSpacing(0)
        self.selector_bar = EntitySelectorBar(
            "Active Analysis",
            store,
            actions,
            lambda: store.project.analyses,
            lambda: controllers.analysis.active_analysis_id,
            controllers.analysis.set_active_analysis,
            (
                A.ANALYSIS_NEW,
                A.ANALYSIS_EDIT,
                A.ANALYSIS_RUN,
            ),
        )
        layout.addWidget(self.selector_bar)
        layout.addWidget(
            RibbonGroup(
                RibbonGroupSpec(
                    "ANALYSIS",
                    (
                        A.VALIDATE,
                        A.PREVIEW_DECK,
                        A.WRITE_DECK,
                        A.SOLVER_SETTINGS,
                        A.DELETE_SELECTED,
                    ),
                ),
                actions,
            )
        )
        layout.addStretch(1)


def create(actions, store, controllers):
    return AnalysisPage(actions, store, controllers)
