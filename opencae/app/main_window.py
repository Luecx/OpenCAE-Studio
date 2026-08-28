"""Main application window and centralized action-state synchronization."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QMessageBox

from opencae.controllers.controller_hub import ControllerHub
from opencae.ui.actions.catalog import register_actions
from opencae.ui.actions.registry import ActionRegistry
from opencae.ui.dialogs.about import AboutDialog
from opencae.ui.menus.menu_bar import build_menus
from opencae.ui.visibility_state import VisibilityState
from . import window_layout


class MainWindow(QMainWindow):
    def __init__(self, context):
        super().__init__()
        self.context = context
        self.visibility = VisibilityState(context.store.project, self)
        self.setWindowTitle("OpenCAE Studio")
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
        self.ribbon.stage_changed.connect(self.controllers.studies.stage_changed)
        window_layout.build_viewport(self)
        window_layout.build_docks(self)
        window_layout.build_status(self)
        context.store.changed.connect(self.refresh_title)
        context.store.changed.connect(self.refresh_action_states)
        context.store.changed.connect(
            lambda *_: self.visibility.sync_project(context.store.project)
        )
        context.store.active_part_changed.connect(self.refresh_action_states)
        context.store.selection_changed.connect(self.refresh_action_states)
        context.store.message.connect(self.statusBar().showMessage)
        self.controllers.jobs.selection_changed.connect(self.refresh_action_states)
        self.controllers.jobs.progress_changed.connect(self.refresh_action_states)
        self.refresh_action_states()

    def refresh_title(self, *_):
        project = self.context.store.project
        self.setWindowTitle(f"OpenCAE Studio — {project.name}")
        self.units.refresh(
            self.context.settings.unit_systems,
            project.unit_system,
        )
        self.units.setToolTip(
            f"Current unit system: {project.unit_system} | "
            f"Solver: {self.context.settings.selected_solver or 'None'}"
        )

    def refresh_action_states(self, *_):
        from opencae.model.entities.resources import Material
        from opencae.ui.actions.ids import A

        part = self.context.store.active_part()
        can_mesh = bool(part and part.geometry and part.mesh.seeds)
        has_part = part is not None
        has_cad = bool(part and part.geometry)
        self.actions.get(A.GENERATE_MESH).setEnabled(can_mesh)
        for action_id in (
            A.DATUM_POINT,
            A.DATUM_VECTOR,
            A.DATUM_PLANE,
            A.PART_RP,
            A.PART_CSYS,
            A.NODE_SET,
            A.ELEMENT_SET,
            A.SURFACE,
            A.SECTION_ASSIGNMENT,
            A.VISIBILITY,
        ):
            self.actions.get(action_id).setEnabled(has_part)
        for action_id in (
            A.PARTITION,
            A.REBUILD_GEOMETRY,
            A.SUPPRESS_FEATURE,
            A.DEFAULT_SEED,
            A.EDGE_SEED,
            A.MESH_SETTINGS,
        ):
            self.actions.get(action_id).setEnabled(has_cad)
        self.actions.get(A.ELEMENT_CONTROLS).setEnabled(
            bool(part and part.mesh.element_blocks)
        )

        project = self.context.store.project
        has_assembly = any(
            not instance.suppressed for instance in project.assembly.instances
        )
        for action_id in (
            A.CONSTRAINT_KINEMATIC,
            A.CONSTRAINT_DISTRIBUTING,
            A.CONSTRAINT_TIE,
            A.CONSTRAINT_RIGID,
            A.CONSTRAINT_EQUATION,
            A.CONSTRAINT_MPC,
            A.FIXED,
            A.DISPLACEMENT,
            A.SYMMETRY,
            A.CLOAD,
            A.DLOAD,
            A.PRESSURE,
            A.VLOAD,
            A.INERTIA_LOAD,
            A.TEMPERATURE,
            A.STEP_LINEAR,
            A.STEP_NONLINEAR,
            A.STEP_MODAL,
            A.STEP_BUCKLING,
            A.STEP_TRANSIENT,
        ):
            self.actions.get(action_id).setEnabled(has_assembly)
        self.actions.get(A.REORDER_STEPS).setEnabled(len(project.steps) > 1)
        self.actions.get(A.STEP_MATRIX).setEnabled(bool(project.steps))

        analysis = self.controllers.analysis.active_analysis()
        analysis_steps = (
            analysis.resolved_steps(project) if analysis is not None else ()
        )
        analysis_solver = getattr(analysis, "solver", "")
        analysis_adapter_ready = bool(
            analysis_solver
            and analysis_solver in self.context.solvers
            and analysis_solver in self.context.settings.enabled_solvers()
        )
        analysis_executable = str(
            self.context.settings.solver_config(analysis_solver).get(
                "executable",
                "",
            )
        ) if analysis_solver else ""
        analysis_runnable = bool(
            analysis
            and analysis_steps
            and has_assembly
            and analysis_adapter_ready
            and Path(analysis_executable).is_file()
        )
        self.actions.get(A.ANALYSIS_NEW).setEnabled(bool(project.steps))
        self.actions.get(A.ANALYSIS_EDIT).setEnabled(analysis is not None)
        self.actions.get(A.SOLVER_SETTINGS).setEnabled(True)
        for action_id in (A.VALIDATE, A.PREVIEW_DECK, A.WRITE_DECK):
            self.actions.get(action_id).setEnabled(
                bool(analysis and analysis_steps and has_assembly and analysis_adapter_ready)
            )
        self.actions.get(A.ANALYSIS_RUN).setEnabled(analysis_runnable)

        study = project.try_resolve(self.controllers.studies.active_study_id)
        has_study = study is not None
        femaster_config = self.context.settings.solver_config("FEMaster")
        femaster_ready = bool(
            "FEMaster" in self.context.solvers
            and "FEMaster" in self.context.settings.enabled_solvers()
            and Path(str(femaster_config.get("executable", ""))).is_file()
        )
        self.actions.get(A.STUDY_NEW_TOPOLOGY).setEnabled(
            bool(has_assembly and project.analyses)
        )
        self.actions.get(A.STUDY_EDIT).setEnabled(has_study)
        for action_id in (
            A.OPT_RESPONSE,
            A.OPT_OBJECTIVE,
            A.OPT_CONSTRAINT,
            A.OPT_FILTER,
            A.OPT_SYMMETRY,
            A.OPT_CONTROLS,
            A.STUDY_VALIDATE,
        ):
            self.actions.get(action_id).setEnabled(has_study)
        self.actions.get(A.STUDY_RUN).setEnabled(
            bool(has_study and has_assembly and femaster_ready)
        )

        jobs = self.controllers.jobs
        self.actions.get(A.JOB_STOP).setEnabled(jobs.can_stop_selected())
        self.actions.get(A.JOB_MONITOR).setEnabled(jobs.can_monitor_selected())
        self.actions.get(A.JOB_OPEN_RESULTS).setEnabled(
            jobs.can_open_selected_results()
        )

        has_iterations = any(
            run.iterations
            for item in project.studies
            for run in getattr(item, "runs", ())
        )
        for action_id in (A.OPT_PREVIOUS, A.OPT_NEXT, A.OPT_THRESHOLD):
            self.actions.get(action_id).setEnabled(has_iterations)

        has_material = isinstance(self.context.store.selection, Material)
        for action_id in (
            A.SET_ELASTICITY,
            A.SET_DENSITY,
            A.SET_PLASTICITY,
            A.SET_THERMAL,
        ):
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

    def delete_result(self, result):
        project = self.context.store.project
        stored = next(
            (
                item
                for item in project.results
                if item.id == getattr(result, "id", None)
            ),
            None,
        )
        if stored is None:
            self.context.store.message.emit(
                "The selected result no longer exists"
            )
            return
        if QMessageBox.question(
            self,
            "Delete result",
            f"Delete the opened result set '{stored.name}'?\n\n"
            "The external result files will not be deleted.",
        ) != QMessageBox.StandardButton.Yes:
            return
        if self.viewport.is_showing_result(stored):
            self.viewport.close_solution(stored)
            if self.ribbon.results_page is not None:
                self.ribbon.results_page.set_solution(None, None)
        self.context.store.delete_entity(
            f"Deleted result {stored.name}",
            project.id,
            "results",
            stored.id,
        )
        self.context.store.message.emit(f"Deleted result {stored.name}")

    def show_documentation(self):
        self.context.store.message.emit("Documentation is not bundled yet")

    def show_shortcuts(self):
        self.context.store.message.emit(
            "Shortcuts: Ctrl+N/O/S, Ctrl+Z/Y, F5, F7, F"
        )

    def reset_layout(self):
        self.addDockWidget(
            Qt.DockWidgetArea.LeftDockWidgetArea,
            self.project_dock,
        )
        for dock in (self.jobs_dock, self.log_dock, self.time_manager_dock):
            self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
            dock.show()
        self.tabifyDockWidget(self.jobs_dock, self.log_dock)
        self.tabifyDockWidget(self.jobs_dock, self.time_manager_dock)
        self.project_dock.show()
        self.jobs_dock.raise_()
        self.ribbon_host.show()

    def show_about(self):
        AboutDialog(self).exec()
