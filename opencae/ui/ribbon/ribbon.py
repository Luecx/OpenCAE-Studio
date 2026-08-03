from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

from opencae.ui.core.metrics import CONTEXT_BAR_HEIGHT, RIBBON_PAGE_HEIGHT
from opencae.ui.core.theme import PALETTE
from . import analysis_page, assembly_page, bc_page, constraints_page, fields_page
from . import materials_page, part_page, profiles_page, results_page, sections_page, solve_page
from .ribbon_page import RibbonPage
from .stage_bar import STAGES, StageBar

_PAGES = (
    materials_page, sections_page, profiles_page, fields_page, part_page, assembly_page,
    constraints_page, bc_page, analysis_page, solve_page, results_page,
)


class Ribbon(QWidget):
    stage_changed = pyqtSignal(str)
    result_requested = pyqtSignal(object, object, dict)

    def __init__(self, actions, store, settings, solvers, state_callback, parent=None):
        super().__init__(parent)
        self.store = store; self.settings = settings; self.solvers = solvers
        self.state_callback = state_callback; self.solve_page = None; self.part_page = None; self.results_page = None; self.current_stage = ""; self.last_project_stage = "PART"
        self.setObjectName("Ribbon")
        self.setStyleSheet(f"QWidget#Ribbon {{ background:{PALETTE['panel']}; border-bottom:1px solid {PALETTE['border']}; }}")
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        self.stage_bar = StageBar(); self.stage_bar.stage_changed.connect(self.set_stage); layout.addWidget(self.stage_bar)
        self.context = self._context_label(); layout.addWidget(self.context)
        self.stack = QStackedWidget(); self.stack.setFixedHeight(RIBBON_PAGE_HEIGHT)
        for module in _PAGES:
            if module is solve_page:
                self.solve_page = module.create(actions, settings, self._solver_changed); page = self.solve_page
            elif module is part_page:
                self.part_page = module.create(actions, store); page = self.part_page
            elif module is results_page:
                self.results_page = module.create(actions); self.results_page.result_requested.connect(self.result_requested); page = self.results_page
            else: page = RibbonPage(module.groups(), actions)
            self.stack.addWidget(page)
        layout.addWidget(self.stack)
        store.changed.connect(self.refresh_context); store.active_part_changed.connect(self.refresh_context)
        self.set_stage("PART")

    def _context_label(self):
        label = QLabel(); label.setFixedHeight(CONTEXT_BAR_HEIGHT)
        label.setStyleSheet(f"background:{PALETTE['panel_alt']}; color:{PALETTE['muted']}; border-top:1px solid {PALETTE['border']}; border-bottom:1px solid {PALETTE['border']}; padding-left:8px;")
        return label

    def set_stage(self, stage):
        if stage not in STAGES or stage == self.current_stage: return
        if stage != "RESULTS":
            self.last_project_stage = stage
        self.current_stage = stage; self.stage_bar.set_stage(stage); self.stack.setCurrentIndex(STAGES.index(stage))
        self.refresh_context(); self.stage_changed.emit(stage)

    def set_browser(self, name):
        if str(name).casefold() == "solution":
            self.set_stage("RESULTS")
        elif self.current_stage == "RESULTS":
            self.set_stage(self.last_project_stage or "PART")

    def refresh_context(self, *_):
        project = self.store.project; part = self.store.active_part(); stage = self.current_stage
        if stage == "MATERIALS": text = f"  Materials: {len(project.materials)}"
        elif stage == "SECTIONS": text = f"  Sections: {len(project.sections)}"
        elif stage == "PROFILES": text = f"  Profiles: {len(project.profiles)}"
        elif stage == "FIELDS": text = f"  Fields: {len(project.fields)}"
        elif stage == "PART":
            text = f"  Active Part: {part.name}     Geometry features: {len(part.geometry)}     Mesh: {part.mesh.status}" if part else "  No active part"
        elif stage == "ASSEMBLY": text = f"  Assembly: {project.assembly.name}     {len(project.assembly.instances)} instances"
        elif stage == "CONSTRAINTS": text = f"  Constraints: {len(project.assembly.constraints)}"
        elif stage == "BOUNDARY CONDITIONS": text = f"  Supports: {len(project.supports)}     Loads: {len(project.loads)}"
        elif stage == "ANALYSIS": text = f"  Steps: {sum(len(item.steps) for item in project.analyses)}"
        elif stage == "SOLVE": text = f"  Active solver: {self.settings.selected_solver or 'No solver'}"
        else: text = f"  Available solutions: {len(project.results)}"
        self.context.setText(text)

    def refresh_solvers(self):
        if self.solve_page is not None: self.solve_page.solver_selector.refresh()
        self.refresh_context()

    def _solver_changed(self):
        self.state_callback(); self.refresh_context()
