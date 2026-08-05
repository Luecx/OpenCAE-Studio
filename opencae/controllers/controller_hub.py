"""Constructs application controllers around one shared project and JobManager."""

from .analysis_controller import AnalysisController
from .assembly_controller import AssemblyController
from .job_manager import JobManager
from .load_controller import LoadController
from .optimization_controller import OptimizationController
from .part_controller import PartController
from .project_controller import ProjectController
from .resource_controller import ResourceController
from .selection_controller import SelectionController
from .solver_controller import SolverController


class ControllerHub:
    def __init__(self, store, parent, settings, solvers):
        self.store = store
        self.parent = parent
        self.project = ProjectController(store, parent, settings)
        self.part = PartController(store, parent)
        self.resources = ResourceController(store, parent)
        self.assembly = AssemblyController(store, parent, self.part)
        self.loads = LoadController(store, parent, self.part, self.resources)
        self.jobs = JobManager(store, parent, settings, solvers)
        self.analysis = AnalysisController(store, parent, settings, self.jobs)
        self.solver = SolverController(store, parent, settings, solvers)
        self.optimization = OptimizationController(
            store,
            parent,
            settings,
            solvers,
            self.jobs,
        )
        self.studies = self.optimization
        self.selection = SelectionController(
            store,
            parent,
            self.part,
            self.resources,
        )

        original_edit = self.selection.edit_selected
        original_delete = self.selection.delete_selected

        def edit_selected():
            from opencae.model.entities.analysis import Analysis
            from opencae.model.entities.optimization import (
                OptimizationConstraint,
                OptimizationIteration,
                OptimizationObjective,
                OptimizationResponse,
                OptimizationRun,
                TopologyControls,
                TopologyFilterSettings,
                TopologyOptimization,
                TopologySymmetry,
            )

            entity = store.selection
            if isinstance(entity, Analysis):
                return self.analysis.edit_analysis(entity)
            if isinstance(
                entity,
                (
                    TopologyOptimization,
                    OptimizationResponse,
                    OptimizationObjective,
                    OptimizationConstraint,
                    TopologyFilterSettings,
                    TopologySymmetry,
                    TopologyControls,
                    OptimizationRun,
                    OptimizationIteration,
                ),
            ):
                return self.optimization.edit(entity)
            return original_edit()

        def delete_selected():
            from opencae.model.entities.jobs import Job
            from opencae.model.entities.optimization import (
                OptimizationRun,
                TopologyControls,
                TopologyFilterSettings,
                TopologyOptimization,
            )

            entity = store.selection
            if isinstance(entity, Job) and entity.id in self.jobs._runners:
                store.message.emit("Stop the job before deleting it")
                return
            if isinstance(entity, OptimizationRun) and entity.job_ref:
                job = store.project.try_resolve(entity.job_ref)
                if job is not None and job.id in self.jobs._runners:
                    store.message.emit(
                        "Stop the job before deleting its topology state"
                    )
                    return
            if isinstance(entity, TopologyOptimization):
                running = any(
                    job.id in self.jobs._runners
                    and job.source_ref
                    and job.source_ref.entity_id == entity.id
                    for job in store.project.jobs
                )
                if running:
                    store.message.emit(
                        "Stop active Study jobs before deleting the Study"
                    )
                    return
            if isinstance(entity, (TopologyControls, TopologyFilterSettings)):
                parent_entity = store.project.try_resolve(
                    store.project.index.parent_id.get(entity.id)
                )
                collection = (
                    parent_entity.controls
                    if isinstance(entity, TopologyControls)
                    else parent_entity.filters
                )
                if len(collection) <= 1:
                    store.message.emit(
                        "A Topology Optimization Study must keep one filter and "
                        "one controls definition"
                    )
                    return
            return original_delete()

        self.selection.edit_selected = edit_selected
        self.selection.delete_selected = delete_selected
        store.selection_changed.connect(self._sync_active_definition)

    def _sync_active_definition(self, entity):
        """Keep tree selection and ribbon selectors on the same definition."""

        from opencae.model.entities.analysis import Analysis
        from opencae.model.entities.optimization import TopologyOptimization

        if isinstance(entity, Analysis):
            self.analysis.active_analysis_id = entity.id
        study = entity if isinstance(entity, TopologyOptimization) else None
        current = entity
        project = self.store.project
        while study is None and current is not None:
            parent_id = project.index.parent_id.get(getattr(current, "id", ""))
            current = project.try_resolve(parent_id) if parent_id else None
            if isinstance(current, TopologyOptimization):
                study = current
        if study is not None:
            self.studies.active_study_id = study.id

        ribbon = getattr(self.parent, "ribbon", None)
        if ribbon is None:
            return
        if isinstance(entity, Analysis) and ribbon.analysis_page is not None:
            ribbon.analysis_page.selector_bar.refresh()
        if study is not None and ribbon.studies_page is not None:
            ribbon.studies_page.selector_bar.refresh()
        ribbon.refresh_context()
