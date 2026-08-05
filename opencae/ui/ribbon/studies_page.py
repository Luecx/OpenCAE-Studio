"""Active Study selector, setup actions and execution ribbon page."""

from PyQt6.QtWidgets import QHBoxLayout, QWidget

from opencae.ui.actions.ids import A
from opencae.ui.core.widgets import EntitySelectorBar

from .ribbon_group import RibbonGroup
from .specs import RibbonGroupSpec


class StudiesPage(QWidget):
    """Select and execute a Study while exposing type-specific setup actions."""

    def __init__(self, actions, store, controllers, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 0, 0)
        layout.setSpacing(0)

        self.selector_bar = EntitySelectorBar(
            "Active Study",
            store,
            lambda: store.project.studies,
            lambda: controllers.studies.active_study_id,
            controllers.studies.set_active_study,
        )
        layout.addWidget(self.selector_bar)

        layout.addWidget(
            RibbonGroup(
                RibbonGroupSpec(
                    "DEFINITION",
                    (
                        A.STUDY_NEW_TOPOLOGY,
                        A.STUDY_EDIT,
                        A.DELETE_SELECTED,
                    ),
                ),
                actions,
            )
        )
        layout.addWidget(
            RibbonGroup(
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
                actions,
            )
        )
        layout.addWidget(
            RibbonGroup(
                RibbonGroupSpec(
                    "STUDY",
                    (
                        A.STUDY_VALIDATE,
                        A.STUDY_RUN,
                    ),
                ),
                actions,
            )
        )
        layout.addStretch(1)


def create(actions, store, controllers):
    return StudiesPage(actions, store, controllers)
