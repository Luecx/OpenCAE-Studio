from .analysis_controller import AnalysisController
from .assembly_controller import AssemblyController
from .load_controller import LoadController
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
        self.selection=SelectionController(store,parent,self.part,self.resources)
