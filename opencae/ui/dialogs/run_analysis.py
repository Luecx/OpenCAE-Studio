"""Confirm solver and input-deck profile before starting an Analysis job."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

from opencae.deck_formats.selection import (
    default_profile_id,
    normalized_profile_id,
    profile_choices,
)
from opencae.ui.core.controls import dialog_buttons
from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.templates import (
    FieldStack,
    LabelRole,
    SectionHeading,
    apply_primary_control_height,
    label,
)


class RunAnalysisDialog(QDialog):
    """Choose the executable solver and compatible deck profile for one run."""

    def __init__(self, analysis, solver_adapters, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Run Analysis")
        self.setMinimumWidth(520)
        self._adapters = dict(solver_adapters)
        self._settings = settings

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)
        root.addWidget(SectionHeading("Run Analysis"))
        subtitle = label(
            f"{analysis.name} — choose the solver and input deck profile used for this submission.",
            role=LabelRole.MUTED,
        )
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        form = FieldStack()
        self.solver = ChevronComboBox()
        for name in self._adapters:
            self.solver.addItem(name, name)
        solver_index = self.solver.findData(analysis.solver)
        self.solver.setCurrentIndex(max(solver_index, 0))
        apply_primary_control_height(self.solver)
        form.addRow("Solver", self.solver)

        self.deck_profile = ChevronComboBox()
        apply_primary_control_height(self.deck_profile)
        form.addRow("Input Deck Profile", self.deck_profile)
        root.addWidget(form)

        self._refresh_profiles(
            reset=False,
            requested=getattr(analysis, "deck_profile_id", ""),
        )
        self.solver.currentIndexChanged.connect(
            lambda _index: self._refresh_profiles(reset=True)
        )

        buttons = dialog_buttons()
        run_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if run_button is not None:
            run_button.setText("Run")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _adapter(self):
        return self._adapters[
            str(self.solver.currentData() or self.solver.currentText())
        ]

    def _refresh_profiles(self, *, reset: bool, requested: str = "") -> None:
        """Refresh choices and reset to the solver's built-in when requested."""
        adapter = self._adapter()
        selected = (
            default_profile_id(adapter)
            if reset
            else normalized_profile_id(self._settings, adapter, requested)
        )
        self.deck_profile.blockSignals(True)
        try:
            self.deck_profile.clear()
            for profile_id, name in profile_choices(self._settings, adapter):
                self.deck_profile.addItem(name, profile_id)
            index = self.deck_profile.findData(selected)
            self.deck_profile.setCurrentIndex(max(index, 0))
        finally:
            self.deck_profile.blockSignals(False)

    def values(self) -> tuple[str, str]:
        """Return the selected solver and stable compatible profile identity."""
        adapter = self._adapter()
        return (
            str(self.solver.currentData()),
            normalized_profile_id(
                self._settings,
                adapter,
                str(self.deck_profile.currentData() or ""),
            ),
        )
