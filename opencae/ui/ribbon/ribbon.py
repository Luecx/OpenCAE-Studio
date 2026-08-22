"""Workflow ribbon with separate Steps, Analysis and Studies stages."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget

from opencae.ui.core.metrics import CONTEXT_BAR_HEIGHT, RIBBON_PAGE_HEIGHT
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
        self.context = self._context_label()
        layout.addWidget(self.context)
        self.stack = QStackedWidget()
        self.stack.setMinimumWidth(0)
        self.stack.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )
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
        store.changed.connect(self.refresh_context)
        store.active_part_changed.connect(self.refresh_context)
        self.set_stage("PART")

    def _context_label(self):
        label = QLabel()
        label.setFixedHeight(CONTEXT_BAR_HEIGHT)
        label.setStyleSheet(
            f"background:{PALETTE['panel_alt']}; color:{PALETTE['muted']}; "
            f"border-top:1px solid {PALETTE['border']}; "
            f"border-bottom:1px solid {PALETTE['border']}; padding-left:8px;"
        )
        return label

    def set_stage(self, stage):
        if stage not in STAGES or stage == self.current_stage:
            return
        if stage != "RESULTS":
            self.last_project_stage = stage
        self.current_stage = stage
        self.stage_bar.set_stage(stage)
        self.stack.setCurrentIndex(STAGES.index(stage))
        self.refresh_context()
        self.stage_changed.emit(stage)

    def set_browser(self, name):
        if str(name).casefold() == "solution":
            self.set_stage("RESULTS")
        elif self.current_stage == "RESULTS":
            self.set_stage(self.last_project_stage or "PART")

    def refresh_context(self, *_):
        project = self.store.project
        part = self.store.active_part()
        stage = self.current_stage
        if stage == "MATERIALS":
            text = f"  Materials: {len(project.materials)}"
        elif stage == "SECTIONS":
            text = f"  Sections: {len(project.sections)}"
        elif stage == "PROFILES":
            text = f"  Profiles: {len(project.profiles)}"
        elif stage == "FIELDS":
            text = f"  Fields: {len(project.fields)}"
        elif stage == "PART":
            text = (
                f"  Active Part: {part.name}     Geometry features: {len(part.geometry)}"
                f"     Mesh: {part.mesh.status}"
                if part
                else "  No active part"
            )
        elif stage == "ASSEMBLY":
            text = (
                f"  Assembly: {project.assembly.name}     "
                f"{len(project.assembly.instances)} instances"
            )
        elif stage == "CONSTRAINTS":
            text = f"  Constraints: {len(project.assembly.constraints)}"
        elif stage == "BOUNDARY CONDITIONS":
            text = f"  Supports: {len(project.supports)}     Loads: {len(project.loads)}"
        elif stage == "STEPS":
            text = f"  Reusable Steps: {len(project.steps)}"
        elif stage == "ANALYSIS":
            active = self.controllers.analysis.active_analysis() if self.controllers else None
            count = len(active.resolved_steps(project)) if active else 0
            text = (
                f"  Active Analysis: {active.name}     Steps: {count}     "
                f"Solver: {active.solver}"
                if active
                else "  No Analysis selected"
            )
        elif stage == "STUDIES":
            active = (
                project.try_resolve(self.controllers.studies.active_study_id)
                if self.controllers
                else None
            )
            text = (
                f"  Active Study: {active.name}     Type: "
                f"{getattr(active, 'study_type', type(active).__name__)}"
                if active
                else "  No Study selected"
            )
        else:
            text = f"  Available solutions: {len(project.results)}"
        self.context.setText(text)

    def refresh_solvers(self):
        if self.analysis_page is not None:
            self.analysis_page.selector_bar.refresh()
        self.refresh_context()

    def _solver_changed(self):
        self.state_callback()
        self.refresh_context()
