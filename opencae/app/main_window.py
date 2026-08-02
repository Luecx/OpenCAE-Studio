from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow
from opencae.controllers.controller_hub import ControllerHub
from opencae.ui.actions.catalog import register_actions
from opencae.ui.actions.registry import ActionRegistry
from opencae.ui.dialogs.about import AboutDialog
from opencae.ui.menus.menu_bar import build_menus
from . import window_layout
class MainWindow(QMainWindow):
    def __init__(self, context):
        super().__init__()
        self.context = context
        self.setWindowTitle("OpenCAE Studio — Bracket Study")
        self.resize(1600, 980)
        self.setDockOptions(
            QMainWindow.DockOption.AllowNestedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.AnimatedDocks
        )
        self.controllers = ControllerHub(
            context.store,
            self,
            context.settings,
            context.solvers,
        )
        self.actions = ActionRegistry(self)
        register_actions(self.actions, self.controllers, self, context.store)
        build_menus(self, self.actions)
        window_layout.build_ribbon(self)
        window_layout.build_viewport(self)
        window_layout.build_docks(self)
        window_layout.build_status(self)
        context.store.changed.connect(self.refresh_title)
        context.store.changed.connect(self.refresh_action_states)
        context.store.active_part_changed.connect(self.refresh_action_states)
        context.store.selection_changed.connect(self.refresh_action_states)
        context.store.message.connect(self.statusBar().showMessage)
        self.refresh_action_states()
    def refresh_title(self, *_):
        project = self.context.store.project
        self.setWindowTitle(f"OpenCAE Studio — {project.name}")
        self.units.refresh(self.context.settings.unit_systems, project.unit_system)
        self.units.setToolTip(f"Current unit system: {project.unit_system} | Solver: {self.context.settings.selected_solver or 'None'}")
    def refresh_action_states(self, *_):
        from opencae.model.entities.resources import Material
        from opencae.ui.actions.ids import A
        part = self.context.store.active_part()
        can_mesh = bool(part and part.geometry and part.mesh.seeds)
        has_part = part is not None; has_cad = bool(part and part.geometry)
        self.actions.get(A.GENERATE_MESH).setEnabled(can_mesh)
        for action_id in (A.DATUM_POINT, A.DATUM_VECTOR, A.DATUM_PLANE, A.PART_RP, A.PART_CSYS, A.NODE_SET, A.ELEMENT_SET, A.SURFACE, A.SECTION_ASSIGNMENT):
            self.actions.get(action_id).setEnabled(has_part)
        for action_id in (A.PARTITION, A.REBUILD_GEOMETRY, A.SUPPRESS_FEATURE, A.DEFAULT_SEED, A.EDGE_SEED, A.MESH_CONTROL, A.MESH_SETTINGS):
            self.actions.get(action_id).setEnabled(has_cad)
        project = self.context.store.project
        has_assembly = any(not instance.suppressed for instance in project.assembly.instances)
        solver_ready = bool(self.context.settings.selected_solver in self.context.settings.enabled_solvers())
        has_steps = bool(project.analyses)
        for action_id in (A.CONSTRAINT_KINEMATIC, A.CONSTRAINT_DISTRIBUTING, A.CONSTRAINT_TIE, A.CONSTRAINT_RIGID, A.CONSTRAINT_EQUATION, A.CONSTRAINT_MPC):
            self.actions.get(action_id).setEnabled(has_assembly)
        for action_id in (A.FIXED, A.DISPLACEMENT, A.SYMMETRY, A.CLOAD, A.DLOAD, A.PRESSURE, A.VLOAD, A.INERTIA_LOAD, A.TEMPERATURE):
            self.actions.get(action_id).setEnabled(has_assembly)
        for action_id in (A.STEP_LINEAR, A.STEP_NONLINEAR, A.STEP_MODAL, A.STEP_BUCKLING, A.STEP_TRANSIENT, A.REORDER_STEPS, A.STEP_MATRIX):
            self.actions.get(action_id).setEnabled(has_assembly)
        for action_id in (A.PREVIEW_DECK, A.WRITE_DECK, A.VALIDATE, A.RUN):
            self.actions.get(action_id).setEnabled(solver_ready and has_steps and has_assembly)
        has_material = isinstance(self.context.store.selection, Material)
        for action_id in (A.SET_ELASTICITY, A.SET_DENSITY, A.SET_PLASTICITY, A.SET_THERMAL):
            self.actions.get(action_id).setEnabled(has_material)
    def fit_view(self):
        self.viewport.fit_view()
    def toggle_mesh(self):
        self.viewport.toggle_mesh()
    def show_solution(self, result, field=None):
        self.ribbon.set_stage("RESULTS")
        self.project_dock.panel.set_browser("solution")
        if self.ribbon.results_page is not None:
            self.ribbon.results_page.set_solution(result, field)
    def show_documentation(self):
        self.context.store.message.emit("Documentation is not bundled yet")
    def show_shortcuts(self):
        self.context.store.message.emit(
            "Shortcuts: Ctrl+N/O/S, Ctrl+Z/Y, F5, F7, F"
        )
    def reset_layout(self):
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.project_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.properties_dock)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.output_dock)
        self.project_dock.show()
        self.properties_dock.show()
        self.output_dock.show()
        self.ribbon_host.show()
    def show_about(self):
        AboutDialog(self).exec()
