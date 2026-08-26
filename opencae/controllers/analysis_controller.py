"""Controls shared Steps and executable Analysis definitions."""

from __future__ import annotations

from copy import deepcopy

from PyQt6.QtWidgets import QDialog

from opencae.deck_formats.selection import default_profile_id
from opencae.model.core import EntityRef
from opencae.model.entities.analysis import Analysis, AnalysisStep
from opencae.model.naming import next_name_from_names
from opencae.solvers.registry import available_solvers
from opencae.store.commands import UpdateFieldCommand
from opencae.ui.dialogs.analysis_dialog import AnalysisDialog
from opencae.ui.dialogs.run_analysis import RunAnalysisDialog
from opencae.ui.dialogs.solver_settings import SolverSettingsDialog
from opencae.ui.dialogs.step import StepDialog
from opencae.ui.dialogs.step_collectors import StepCollectorsDialog
from opencae.ui.dialogs.step_reorder import StepReorderDialog


class AnalysisController:
    """Own the active Analysis UI state and all Step/Analysis mutations."""

    def __init__(self, store, parent, settings, jobs=None):
        self.store = store
        self.parent = parent
        self.settings = settings
        self.jobs = jobs
        self.active_analysis_id = ""
        store.changed.connect(self._repair_active_analysis)
        self._repair_active_analysis()

    def _solver_adapters(self):
        """Return the runtime solver registry shared with the Job manager."""
        if self.jobs is not None and getattr(self.jobs, "solvers", None):
            return self.jobs.solvers
        return available_solvers()

    def active_analysis(self):
        project = self.store.project
        current = project.try_resolve(self.active_analysis_id)
        if isinstance(current, Analysis):
            return current
        return project.analyses[0] if project.analyses else None

    def set_active_analysis(self, analysis_id):
        value = self.store.project.try_resolve(str(analysis_id or ""))
        self.active_analysis_id = value.id if isinstance(value, Analysis) else ""
        if value is not None:
            self.store.select(value)
        self.parent.refresh_action_states()

    def _repair_active_analysis(self, *_):
        current = self.store.project.try_resolve(self.active_analysis_id)
        if not isinstance(current, Analysis):
            self.active_analysis_id = (
                self.store.project.analyses[0].id
                if self.store.project.analyses
                else ""
            )

    def create_step(self, step_type):
        project = self.store.project
        name = next_name_from_names(
            step_type,
            [step.name for step in project.steps],
        )
        step = AnalysisStep(
            name=name,
            step_type=step_type,
            load_refs=(
                []
                if step_type == "Eigenfrequency"
                else [EntityRef.of(item, "Load") for item in project.loads]
            ),
            support_refs=[
                EntityRef.of(item, "Support") for item in project.supports
            ],
            number_of_modes=10,
        )
        self.store.add_entity(
            f"Created step {name}",
            project.id,
            "steps",
            step,
        )
        created = self.store.project.try_resolve(step.id)
        if created is not None:
            self.store.select(created)
            self.edit_step(created)

    def edit_step(self, step):
        project = self.store.project
        stored = project.try_resolve(step.id)
        if not isinstance(stored, AnalysisStep):
            self.store.message.emit("The selected step no longer exists")
            return
        dialog = StepDialog(
            stored,
            project.loads,
            project.supports,
            self.parent,
            [item.name for item in project.steps],
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        replacement = deepcopy(stored)
        old_name = replacement.name
        replacement.name = values["name"]
        replacement.number_of_modes = values["number_of_modes"]
        replacement.load_refs = [
            EntityRef(entity_id, "Load") for entity_id in values["load_ids"]
        ]
        replacement.support_refs = [
            EntityRef(entity_id, "Support")
            for entity_id in values["support_ids"]
        ]
        self.store.replace_entity(
            f"Edited step {old_name}",
            project.id,
            "steps",
            replacement,
        )
        self.store.select(self.store.project.try_resolve(replacement.id))

    def reorder_steps(self):
        project = self.store.project
        if len(project.steps) < 2:
            return
        dialog = StepReorderDialog(
            [item.name for item in project.steps],
            self.parent,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        rank = {name: index for index, name in enumerate(dialog.order())}
        before = deepcopy(project.steps)
        after = sorted(deepcopy(project.steps), key=lambda item: rank[item.name])
        self.store.execute(
            "Reordered steps",
            UpdateFieldCommand(project.id, "steps", before, after),
        )

    def manage_collectors(self):
        project = self.store.project
        if not project.steps:
            return
        dialog = StepCollectorsDialog(
            project.steps,
            project.loads,
            project.supports,
            self.parent,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        after = deepcopy(project.steps)
        by_id = {step.id: step for step in after}
        for step_id, collector_ids in values.items():
            target = by_id.get(step_id)
            if target is None:
                continue
            target.support_refs = [
                EntityRef(entity_id, "Support")
                for entity_id in collector_ids["support_ids"]
            ]
            target.load_refs = [
                EntityRef(entity_id, "Load")
                for entity_id in collector_ids["load_ids"]
            ]
        self.store.execute(
            "Updated step collectors",
            UpdateFieldCommand(
                project.id,
                "steps",
                deepcopy(project.steps),
                after,
            ),
        )

    def new_analysis(self):
        project = self.store.project
        adapters = self._solver_adapters()
        preferred = self.settings.selected_solver
        solver = preferred if preferred in adapters else next(iter(adapters), "FEMaster")
        adapter = adapters.get(solver)
        value = Analysis(
            name=next_name_from_names(
                "Analysis",
                [item.name for item in project.analyses],
            ),
            solver=solver,
            deck_profile_id=(
                default_profile_id(adapter)
                if adapter is not None
                else "builtin:femaster"
            ),
        )
        self._analysis_dialog(value, None)

    def edit_active_analysis(self):
        analysis = self.active_analysis()
        if analysis is None:
            self.store.message.emit("Create an Analysis first")
            return
        self.edit_analysis(analysis)

    def edit_analysis(self, analysis):
        stored = self.store.project.try_resolve(analysis.id)
        if not isinstance(stored, Analysis):
            self.store.message.emit("The selected Analysis no longer exists")
            return
        self._analysis_dialog(stored, stored)

    def _analysis_dialog(self, value, current):
        project = self.store.project
        dialog = AnalysisDialog(
            value,
            project.steps,
            self._solver_adapters(),
            self.settings,
            existing_names=[item.name for item in project.analyses],
            parent=self.parent,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        candidate = dialog.result()
        if current is None:
            self.store.add_entity(
                f"Created Analysis {candidate.name}",
                project.id,
                "analyses",
                candidate,
            )
        else:
            self.store.replace_entity(
                f"Edited Analysis {candidate.name}",
                project.id,
                "analyses",
                candidate,
            )
        created = self.store.project.try_resolve(candidate.id)
        self.active_analysis_id = candidate.id
        self.store.select(created)

    def run_active(self):
        analysis = self.active_analysis()
        if analysis is None:
            self.store.message.emit("Create an Analysis first")
            return
        if self.jobs is None:
            self.store.message.emit("The job manager is unavailable")
            return

        dialog = RunAnalysisDialog(
            analysis,
            self._solver_adapters(),
            self.settings,
            self.parent,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        solver, profile_id = dialog.values()
        if solver != analysis.solver or profile_id != analysis.deck_profile_id:
            candidate = deepcopy(analysis)
            candidate.solver = solver
            candidate.deck_profile_id = profile_id
            self.store.replace_entity(
                f"Updated run configuration for {analysis.name}",
                self.store.project.id,
                "analyses",
                candidate,
            )
            analysis = self.store.project.resolve(candidate.id)
        self.jobs.run_analysis(analysis.id)

    def validate_active(self):
        analysis = self.active_analysis()
        if analysis is None:
            self.store.message.emit("Create an Analysis first")
            return
        if self.jobs is not None:
            self.jobs.validate_analysis(analysis.id)

    def settings_dialog(self):
        dialog = SolverSettingsDialog(
            self.settings.solver_configs,
            self.parent,
        )
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
