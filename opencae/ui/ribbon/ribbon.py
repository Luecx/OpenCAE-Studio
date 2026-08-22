"""Workflow ribbon with separate Steps, Analysis and Studies stages."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from opencae.ui.core.metrics import RIBBON_PAGE_HEIGHT
from opencae.ui.core.theme import PALETTE
from . import (
    analysis_page,
    assembly_page,
    bc_page,
    constraints_page,
    fields_page,
    materials_page,
    part_page,
    profiles_page,
    results_page,
    sections_page,
    steps_page,
    studies_page,
)
from .ribbon_page import RibbonPage
from .stage_bar import STAGES, StageBar

_PAGES = (
    materials_page,
    sections_page,
    profiles_page,
    fields_page,
    part_page,
    assembly_page,
    constraints_page,
    bc_page,
    steps_page,
    analysis_page,
    studies_page,
    results_page,
)


class Ribbon(QWidget):
    stage_changed = pyqtSignal(str)
    result_requested = pyqtSignal(object, object, dict)

    def __init__(
        self,
        actions,
        store,
        settings,
        solvers,
        state_callback,
        controllers=None,
        parent=None,
    ):
        super().__init__(parent)
        self.store = store
        self.settings = settings
        self.solvers = solvers
        self.controllers = controllers
        self.state_callback = state_callback
        self.part_page = None
        self.analysis_page = None
        self.studies_page = None
        self.results_page = None
        self.current_stage = ""
        self.last_project_stage = "PART"
        self.setObjectName("Ribbon")
        self.setStyleSheet(
            f"QWidget#Ribbon {{ background:{PALETTE['panel']}; "
            f"border-bottom:1px solid {PALETTE['border']}; }}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.stage_bar = StageBar()
        self.stage_bar.stage_changed.connect(self.set_stage)
        layout.addWidget(self.stage_bar)
        self.stack = QStackedWidget()
        self.stack.setFixedHeight(RIBBON_PAGE_HEIGHT)
        for module in _PAGES:
            if module is part_page:
                self.part_page = module.create(actions, store)
                page = self.part_page
            elif module is analysis_page:
                self.analysis_page = (
                    module.create(actions, store, controllers)
                    if controllers is not None
                    else QWidget()
                )
                page = self.analysis_page
            elif module is studies_page:
                self.studies_page = (
                    module.create(actions, store, controllers)
                    if controllers is not None
                    else QWidget()
                )
                page = self.studies_page
            elif module is results_page:
                self.results_page = module.create(actions, store)
                self.results_page.result_requested.connect(self.result_requested)
                page = self.results_page
            else:
                page = RibbonPage(module.groups(), actions)
            self.stack.addWidget(page)
        layout.addWidget(self.stack)
        self.set_stage("PART")

    def set_stage(self, stage):
        if stage not in STAGES or stage == self.current_stage:
            return
        if stage != "RESULTS":
            self.last_project_stage = stage
        self.current_stage = stage
        self.stage_bar.set_stage(stage)
        self.stack.setCurrentIndex(STAGES.index(stage))
        self.stage_changed.emit(stage)

    def set_browser(self, name):
        if str(name).casefold() == "solution":
            self.set_stage("RESULTS")
        elif self.current_stage == "RESULTS":
            self.set_stage(self.last_project_stage or "PART")

    def refresh_context(self, *_):
        # Kept as a compatibility hook for callers that previously refreshed
        # the removed ribbon context/status row.
        return None

    def refresh_solvers(self):
        if self.analysis_page is not None:
            self.analysis_page.selector_bar.refresh()

    def _solver_changed(self):
        self.state_callback()
