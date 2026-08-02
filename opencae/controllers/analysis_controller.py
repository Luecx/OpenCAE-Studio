from PyQt6.QtWidgets import QDialog

from opencae.model.analysis import AnalysisStep, create_analysis
from opencae.model.naming import next_name_from_names
from opencae.ui.dialogs.solver_settings import SolverSettingsDialog
from opencae.ui.dialogs.step import StepDialog
from opencae.ui.dialogs.step_collectors import StepCollectorsDialog
from opencae.ui.dialogs.step_reorder import StepReorderDialog


class AnalysisController:
    def __init__(self, store, parent, settings): self.store=store; self.parent=parent; self.settings=settings

    def create_step(self, analysis_type):
        names = [analysis.steps[0].name for analysis in self.store.project.analyses if analysis.steps]
        name = next_name_from_names(analysis_type, names)
        step=AnalysisStep(name=name,step_type=analysis_type,active_loads=[] if analysis_type=="Eigenfrequency" else [x.name for x in self.store.project.loads],active_supports=[x.name for x in self.store.project.supports],number_of_modes=10)
        analysis=create_analysis(analysis_type,name=name,steps=[step])
        self.store.mutate(f"Created step {name}",lambda project:project.analyses.append(analysis)); self.store.select(step); self.edit_step(step)

    def edit_step(self, step):
        dialog=StepDialog(step,[item.name for item in self.store.project.loads],[item.name for item in self.store.project.supports],self.parent,[a.steps[0].name for a in self.store.project.analyses if a.steps])
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        values=dialog.values()
        def apply(_project):
            old=step.name; step.name=values["name"]; step.number_of_modes=values["number_of_modes"]
            step.active_loads=values["active_loads"]; step.active_supports=values["active_supports"]
            analysis=self._analysis_for(step)
            if analysis and analysis.name==old:analysis.name=step.name
        self.store.mutate(f"Edited step {step.name}",apply)

    def reorder_steps(self):
        analyses=self.store.project.analyses
        if len(analyses)<2:return
        dialog=StepReorderDialog([item.steps[0].name for item in analyses],self.parent)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        order=dialog.order()
        self.store.mutate("Reordered steps",lambda project:project.analyses.sort(key=lambda a:order.index(a.steps[0].name)))

    def manage_collectors(self):
        steps=[analysis.steps[0] for analysis in self.store.project.analyses if analysis.steps]
        if not steps:return
        dialog=StepCollectorsDialog(steps,[x.name for x in self.store.project.loads],[x.name for x in self.store.project.supports],self.parent)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        self.store.mutate("Updated step collectors",lambda _project:dialog.apply())

    def settings_dialog(self):
        dialog=SolverSettingsDialog(self.settings.solver_configs,self.parent)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        self.settings.solver_configs=dialog.values(); enabled=self.settings.enabled_solvers()
        if self.settings.selected_solver not in enabled:self.settings.selected_solver=enabled[0] if enabled else ""
        self.store.message.emit("Solver settings updated"); ribbon=getattr(self.parent,"ribbon",None)
        if ribbon and hasattr(ribbon,"refresh_solvers"):ribbon.refresh_solvers()
        self.parent.refresh_action_states()

    def validate(self):
        project=self.store.project; issues=[]
        if not project.parts:issues.append("No parts defined")
        if not project.assembly.instances:issues.append("No assembly instances")
        if not project.analyses:issues.append("No steps defined")
        self.store.message.emit("Model validation passed" if not issues else "Validation: "+", ".join(issues))

    def _analysis_for(self,step): return next((a for a in self.store.project.analyses if step in a.steps),None)
