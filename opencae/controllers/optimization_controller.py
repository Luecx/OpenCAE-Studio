"""Composes topology Study setup, selection and job-backed display behavior."""

from __future__ import annotations

from opencae.model.entities.optimization import TopologyOptimization
from opencae.model.entities.studies import Study, MeshConvergenceStudy
from opencae.ui.dialogs.mesh_convergence import MeshConvergenceDialog, ConvergenceReportDialog
from opencae.ui.core.dialog_lifecycle import show_modeless_dialog
from opencae.ui.viewport.topology_overlay import TopologyDensityOverlay

from .optimization_run_controller import OptimizationRunMixin
from .optimization_selection_controller import OptimizationSelectionMixin
from .optimization_setup_controller import OptimizationSetupMixin


class OptimizationController(
    OptimizationSetupMixin,
    OptimizationRunMixin,
    OptimizationSelectionMixin,
):
    """Controller for the current topology Study and its definition children."""

    def __init__(self, store, parent, settings, solvers, jobs):
        self.store = store
        self.parent = parent
        self.settings = settings
        self.solvers = solvers
        self.jobs = jobs
        self.active_study_id = ""
        self._dialogs = []
        self._run_dialogs = {}
        self._display_iteration = {}
        self._threshold = None
        self._overlay = TopologyDensityOverlay()
        self._pending_display = None
        store.selection_changed.connect(self._selection_changed)
        store.changed.connect(self._repair_active_study)
        self._repair_active_study()

    def studies(self):
        return tuple(self.store.project.studies)

    def set_active_study(self, study_id):
        value = self.store.project.try_resolve(str(study_id or ""))
        self.active_study_id = value.id if isinstance(value, Study) else ""
        if value is not None:
            self.store.select(value)
        self.parent.refresh_action_states()

    def _repair_active_study(self, *_):
        current = self.store.project.try_resolve(self.active_study_id)
        if not isinstance(current, Study):
            self.active_study_id = (
                self.store.project.studies[0].id
                if self.store.project.studies
                else ""
            )

    def edit_active_study(self):
        study = self.store.project.try_resolve(self.active_study_id)
        if isinstance(study, MeshConvergenceStudy):
            return self.new_mesh_convergence(study)
        study = self._optimization()
        if study is None:
            return self._need_optimization()
        self.store.select(study)
        self.new_topology()

    def new_mesh_convergence(self, current=None):
        """Create a Study unless an actual persisted Study was passed for editing.

        QAction.triggered and QPushButton.clicked may pass a checked bool. Never
        mistake that bool for an existing entity and call replace_entity on a
        freshly generated identity.
        """
        current = current if isinstance(current, MeshConvergenceStudy) else None
        if current is not None:
            current = self.store.project.try_resolve(current.id)
            if not isinstance(current, MeshConvergenceStudy):
                self.store.message.emit("The Study being edited no longer exists")
                return
        dialog = MeshConvergenceDialog(self.store.project, current, self.parent)
        self._dialogs.append(dialog)
        existing_id = current.id if current is not None else ""

        def commit():
            study = dialog.study()
            if not isinstance(study, MeshConvergenceStudy):
                return
            store = self.store
            project = store.project
            if existing_id:
                # Resolve again after modeless editing: the original may have
                # been deleted or changed while the dialog was open.
                if not isinstance(project.try_resolve(existing_id), MeshConvergenceStudy):
                    store.message.emit("Study no longer exists; changes were not saved")
                    return
                study.id = existing_id
                store.replace_entity(
                    f"Edited Study {study.name}", project.id, "studies", study
                )
            else:
                store.add_entity(
                    f"Created Study {study.name}", project.id, "studies", study
                )
            self.active_study_id = study.id
            store.select(store.project.resolve(study.id))

        dialog.accepted.connect(commit)
        dialog.finished.connect(
            lambda _code: self._dialogs.remove(dialog) if dialog in self._dialogs else None
        )
        show_modeless_dialog(dialog)

    def convergence_report(self):
        study = self.store.project.try_resolve(self.active_study_id)
        if not isinstance(study, MeshConvergenceStudy):
            self.store.message.emit("Select a Mesh Convergence Study first")
            return
        ConvergenceReportDialog(study, self.parent).exec()
