from __future__ import annotations

from opencae.optimization import TopologyOptimizationRunner
from opencae.ui.dialogs.topology_run import TopologyRunDialog
from opencae.ui.viewport.topology_overlay import TopologyDensityOverlay

from .optimization_run_controller import OptimizationRunMixin
from .optimization_selection_controller import OptimizationSelectionMixin
from .optimization_setup_controller import OptimizationSetupMixin


class OptimizationController(
    OptimizationSetupMixin, OptimizationRunMixin, OptimizationSelectionMixin
):
    def __init__(self, store, parent, settings, solvers):
        self.store = store
        self.parent = parent
        self.settings = settings
        self.solvers = solvers
        self._dialogs = []
        self._runners: dict[str, TopologyOptimizationRunner] = {}
        self._run_dialogs: dict[str, TopologyRunDialog] = {}
        self._display_iteration: dict[str, int] = {}
        self._threshold = 0.30
        self._overlay = TopologyDensityOverlay()
        self._pending_display = None
        store.selection_changed.connect(self._selection_changed)
