from .analysis_controller import AnalysisController
from .assembly_controller import AssemblyController
from .load_controller import LoadController
from .optimization_controller import OptimizationController
from .part_controller import PartController
from .project_controller import ProjectController
from .resource_controller import ResourceController
from .selection_controller import SelectionController
from .solver_controller import SolverController


class ControllerHub:
    def __init__(self, store, parent, settings, solvers):
        self.project=ProjectController(store,parent,settings)
        self.part=PartController(store,parent)
        self.resources=ResourceController(store,parent)
        self.assembly=AssemblyController(store,parent,self.part)
        self.loads=LoadController(store,parent,self.part,self.resources)
        self.analysis=AnalysisController(store,parent,settings)
        self.solver=SolverController(store,parent,settings,solvers)
        self.optimization=OptimizationController(store,parent,settings,solvers)
        self.selection=SelectionController(store,parent,self.part,self.resources)

        # Keep the generic selection controller focused on the established
        # model entities while routing topology entities to their dedicated
        # editors. The action registry binds this wrapped function afterwards.
        original_edit = self.selection.edit_selected
        original_delete = self.selection.delete_selected

        def edit_selected():
            from opencae.model.entities.optimization import (
                OptimizationConstraint, OptimizationIteration, OptimizationObjective,
                OptimizationResponse, OptimizationRun, TopologyControls,
                TopologyFilterSettings, TopologyOptimization, TopologySymmetry,
            )
            entity = store.selection
            if isinstance(entity, (
                TopologyOptimization, OptimizationResponse, OptimizationObjective,
                OptimizationConstraint, TopologyFilterSettings, TopologySymmetry,
                TopologyControls, OptimizationRun, OptimizationIteration,
            )):
                return self.optimization.edit(entity)
            return original_edit()

        def delete_selected():
            from opencae.model.entities.optimization import OptimizationRun, TopologyOptimization
            entity = store.selection
            active = set(self.optimization._runners)
            if isinstance(entity, OptimizationRun) and entity.id in active:
                store.message.emit("Stop the topology optimization before deleting its run")
                return
            if isinstance(entity, TopologyOptimization):
                if any(run.id in active for run in entity.runs):
                    store.message.emit("Stop all active runs before deleting the topology optimization")
                    return
            from opencae.model.entities.optimization import TopologyControls, TopologyFilterSettings
            if isinstance(entity, (TopologyControls, TopologyFilterSettings)):
                parent = store.project.try_resolve(store.project.index.parent_id.get(entity.id))
                collection = parent.controls if isinstance(entity, TopologyControls) else parent.filters
                if len(collection) <= 1:
                    store.message.emit("A topology optimization must keep one filter and one controls definition")
                    return
            return original_delete()

        self.selection.edit_selected = edit_selected
        self.selection.delete_selected = delete_selected
