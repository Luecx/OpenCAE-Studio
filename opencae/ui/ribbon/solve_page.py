from PyQt6.QtWidgets import QHBoxLayout, QWidget

from opencae.ui.actions.ids import A
from .ribbon_group import RibbonGroup
from .solver_selector import SolverSelector
from .specs import RibbonGroupSpec


def create(actions, settings, changed):
    page = QWidget(); layout = QHBoxLayout(page); layout.setContentsMargins(5, 0, 0, 0); layout.setSpacing(0)
    page.solver_selector = SolverSelector(settings, changed); layout.addWidget(page.solver_selector)
    layout.addWidget(RibbonGroup(RibbonGroupSpec("INPUT DECK", (A.PREVIEW_DECK, A.WRITE_DECK)), actions))
    layout.addWidget(RibbonGroup(RibbonGroupSpec("JOBS", (A.VALIDATE, A.RUN)), actions))
    layout.addStretch(1)
    return page
