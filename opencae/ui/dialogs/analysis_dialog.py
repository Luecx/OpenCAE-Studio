"""Edits an Analysis and its ordered references to shared project steps."""

from __future__ import annotations

from copy import deepcopy

from PyQt6.QtWidgets import QMessageBox

from opencae.deck_formats.selection import (
    default_profile_id,
    normalized_profile_id,
    profile_choices,
)
from opencae.model.core import EntityRef
from opencae.ui.core.named_entity_dialog import NamedEntityDialog
from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.templates import CheckList, SectionHeading, apply_primary_control_height


class AnalysisDialog(NamedEntityDialog):
    """Create or edit an analysis without owning or duplicating its steps."""

    def __init__(
        self,
        value,
        steps,
        solver_adapters,
        settings,
        *,
        existing_names=(),
        parent=None,
    ):
        """Build solver/profile selection and an ordered list of referenced steps."""
        super().__init__(
            "Analysis",
            value,
            existing_names=existing_names,
            parent=parent,
            width=620,
        )
        self._steps = tuple(steps)
        self._solver_adapters = dict(solver_adapters)
        self._settings = settings
        selected = {ref.entity_id for ref in value.step_refs}

        self.solver = ChevronComboBox()
        self.solver.setMinimumWidth(0)
        for name in self._solver_adapters:
            self.solver.addItem(str(name), str(name))
        index = self.solver.findData(value.solver)
        self.solver.setCurrentIndex(max(index, 0))
        apply_primary_control_height(self.solver)
        self.form.addRow("Solver", self.solver)

        self.deck_profile = ChevronComboBox()
        self.deck_profile.setMinimumWidth(0)
        apply_primary_control_height(self.deck_profile)
        self.form.addRow("Input Deck Profile", self.deck_profile)
        self._refresh_profiles(reset=False)
        current_profile = normalized_profile_id(
            self._settings,
            self._current_adapter(),
            getattr(value, "deck_profile_id", ""),
        )
        profile_index = self.deck_profile.findData(current_profile)
        self.deck_profile.setCurrentIndex(max(profile_index, 0))
        self.solver.currentIndexChanged.connect(
            lambda _index: self._refresh_profiles(reset=True)
        )

        self.add_widget(SectionHeading("Referenced Steps"))
        step_options = [
            (f"{step.name}  [{step.step_type}]", step.id)
            for step in self._steps
        ]
        self.step_list = CheckList(step_options, selected)
        self.step_list.setMinimumHeight(240)
        self.add_widget(self.step_list)
        self.finish()

    def _current_adapter(self):
        """Return the adapter selected by the solver control."""
        return self._solver_adapters[
            str(self.solver.currentData() or self.solver.currentText())
        ]

    def _refresh_profiles(self, *, reset: bool) -> None:
        """Show only profiles compatible with the selected solver."""
        adapter = self._current_adapter()
        previous = str(self.deck_profile.currentData() or "")
        self.deck_profile.blockSignals(True)
        try:
            self.deck_profile.clear()
            for profile_id, name in profile_choices(self._settings, adapter):
                self.deck_profile.addItem(name, profile_id)
            selected = default_profile_id(adapter) if reset else previous
            index = self.deck_profile.findData(selected)
            self.deck_profile.setCurrentIndex(max(index, 0))
        finally:
            self.deck_profile.blockSignals(False)

    def result(self):
        """Return a detached Analysis candidate referencing checked shared steps in order."""
        candidate = self.apply_name(deepcopy(self.value))
        candidate.solver = str(self.solver.currentData() or "FEMaster")
        candidate.deck_profile_id = normalized_profile_id(
            self._settings,
            self._current_adapter(),
            str(self.deck_profile.currentData() or ""),
        )
        candidate.step_refs = [
            EntityRef(str(step_id), "AnalysisStep")
            for step_id in self.step_list.selected_values()
        ]
        return candidate

    def validate(self) -> bool:
        """Require valid naming and at least one referenced shared analysis step."""
        if not super().validate():
            return False
        if not self.step_list.selected_values():
            QMessageBox.warning(
                self,
                "Missing steps",
                "Select at least one shared step for this analysis.",
            )
            return False
        return True
