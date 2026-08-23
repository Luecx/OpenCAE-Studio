"""Composes topology Study setup, selection and job-backed display behavior."""

from __future__ import annotations

from opencae.model.entities.optimization import TopologyOptimization
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
        self.active_study_id = value.id if isinstance(value, TopologyOptimization) else ""
        if value is not None:
            self.store.select(value)
        self.parent.refresh_action_states()

    def _repair_active_study(self, *_):
        current = self.store.project.try_resolve(self.active_study_id)
        if not isinstance(current, TopologyOptimization):
            self.active_study_id = (
                self.store.project.studies[0].id
                if self.store.project.studies
                else ""
            )

    def edit_active_study(self):
        study = self._optimization()
        if study is None:
            return self._need_optimization()
        self.store.select(study)
        self.new_topology()
