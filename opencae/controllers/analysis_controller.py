from __future__ import annotations

from copy import deepcopy

from PyQt6.QtWidgets import QDialog

from opencae.model.analysis import AnalysisStep, create_analysis
from opencae.model.core import EntityRef
from opencae.model.naming import next_name_from_names
from opencae.store.commands import UpdateFieldCommand
from opencae.ui.dialogs.solver_settings import SolverSettingsDialog
from opencae.ui.dialogs.step import StepDialog
from opencae.ui.dialogs.step_collectors import StepCollectorsDialog
from opencae.ui.dialogs.step_reorder import StepReorderDialog


class AnalysisController:
    def __init__(self, store, parent, settings):
        self.store = store
        self.parent = parent
        self.settings = settings

    def create_step(self, analysis_type):
        project = self.store.project
        names = [analysis.steps[0].name for analysis in project.analyses if analysis.steps]
        name = next_name_from_names(analysis_type, names)
        step = AnalysisStep(
            name=name,
            step_type=analysis_type,
            load_refs=[] if analysis_type == "Eigenfrequency" else [EntityRef.of(item, "Load") for item in project.loads],
            support_refs=[EntityRef.of(item, "Support") for item in project.supports],
            number_of_modes=10,
        )
        analysis = create_analysis(analysis_type, name=name, steps=[step])
        self.store.add_entity(f"Created step {name}", project.id, "analyses", analysis)
        created = self.store.project.try_resolve(step.id)
        if created is not None:
            self.store.select(created)
            self.edit_step(created)

    def edit_step(self, step):
        project = self.store.project
        analysis = self._analysis_for_id(step.id)
        if analysis is None:
            self.store.message.emit("The selected step no longer exists")
            return
        stored_step = next(item for item in analysis.steps if item.id == step.id)
        dialog = StepDialog(
            stored_step,
            project.loads,
            project.supports,
            self.parent,
            [item.steps[0].name for item in project.analyses if item.steps],
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        replacement = deepcopy(analysis)
        target = next(item for item in replacement.steps if item.id == step.id)
        old_name = target.name
        target.name = values["name"]
        target.number_of_modes = values["number_of_modes"]
        target.load_refs = [EntityRef(entity_id, "Load") for entity_id in values["load_ids"]]
        target.support_refs = [EntityRef(entity_id, "Support") for entity_id in values["support_ids"]]
        if replacement.name == old_name:
            replacement.name = target.name
        self.store.replace_entity(f"Edited step {old_name}", project.id, "analyses", replacement)
        current = self.store.project.try_resolve(step.id)
        if current is not None:
            self.store.select(current)

    def reorder_steps(self):
        project = self.store.project
        analyses = project.analyses
        if len(analyses) < 2:
            return
        dialog = StepReorderDialog([item.steps[0].name for item in analyses], self.parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        order = dialog.order()
        rank = {name: index for index, name in enumerate(order)}
        after = sorted(deepcopy(analyses), key=lambda item: rank[item.steps[0].name])
        self.store.execute("Reordered steps", UpdateFieldCommand(project.id, "analyses", deepcopy(analyses), after))

    def manage_collectors(self):
        project = self.store.project
        steps = [analysis.steps[0] for analysis in project.analyses if analysis.steps]
        if not steps:
            return
        dialog = StepCollectorsDialog(steps, project.loads, project.supports, self.parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        after = deepcopy(project.analyses)
        by_id = {analysis.steps[0].id: analysis.steps[0] for analysis in after if analysis.steps}
        for step_id, collector_ids in values.items():
            target = by_id.get(step_id)
            if target is None:
                continue
            target.support_refs = [EntityRef(entity_id, "Support") for entity_id in collector_ids["support_ids"]]
            target.load_refs = [EntityRef(entity_id, "Load") for entity_id in collector_ids["load_ids"]]
        self.store.execute(
            "Updated step collectors",
            UpdateFieldCommand(project.id, "analyses", deepcopy(project.analyses), after),
        )

    def settings_dialog(self):
        dialog = SolverSettingsDialog(self.settings.solver_configs, self.parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.settings.solver_configs = dialog.values()
        enabled = self.settings.enabled_solvers()
        if self.settings.selected_solver not in enabled:
            self.settings.selected_solver = enabled[0] if enabled else ""
        self.store.message.emit("Solver settings updated")
        ribbon = getattr(self.parent, "ribbon", None)
        if ribbon and hasattr(ribbon, "refresh_solvers"):
            ribbon.refresh_solvers()
        self.parent.refresh_action_states()

    def validate(self):
        from opencae.model.validation import validate_project

        issues = validate_project(self.store.project)
        self.store.message.emit("Model validation passed" if not issues else "Validation: " + ", ".join(issues))

    def _analysis_for_id(self, step_id):
        return next(
            (analysis for analysis in self.store.project.analyses if any(item.id == step_id for item in analysis.steps)),
            None,
        )
