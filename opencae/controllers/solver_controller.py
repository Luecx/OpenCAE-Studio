"""Provides input-deck utilities for the active Analysis."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from opencae.model.entities.analysis import Analysis
from opencae.ui.dialogs.deck_preview import DeckPreviewDialog


class SolverController:
    """Preview and export decks; execution is owned exclusively by JobManager."""

    def __init__(self, store, parent, settings, solvers):
        self.store = store
        self.parent = parent
        self.settings = settings
        self.solvers = solvers

    def _analysis(self):
        controllers = getattr(self.parent, "controllers", None)
        if controllers is not None:
            value = controllers.analysis.active_analysis()
            if isinstance(value, Analysis):
                return value
        selected = self.store.selection
        if isinstance(selected, Analysis):
            return self.store.project.try_resolve(selected.id)
        return self.store.project.analyses[0] if self.store.project.analyses else None

    def _adapter(self, analysis=None):
        value = analysis or self._analysis()
        return self.solvers.get(value.solver) if isinstance(value, Analysis) else None

    def deck_text(self):
        analysis = self._analysis()
        adapter = self._adapter(analysis)
        if analysis is None:
            raise ValueError("Select an Analysis first")
        if adapter is None:
            raise ValueError(f"The Analysis solver {analysis.solver!r} is disabled")
        if not analysis.resolved_steps(self.store.project):
            raise ValueError("The Analysis references no existing Steps")
        if not any(
            not item.suppressed
            for item in self.store.project.assembly.instances
        ):
            raise ValueError(
                "Create at least one assembly instance before exporting an Analysis"
            )
        return adapter.write_deck_text(self.store.project, analysis)

    def validate(self):
        analysis = self._analysis()
        if analysis is None:
            self.store.message.emit("Select an Analysis first")
            return
        self.parent.controllers.jobs.validate_analysis(analysis.id)

    def preview(self):
        try:
            text = self.deck_text()
        except Exception as exc:
            QMessageBox.warning(self.parent, "Deck unavailable", str(exc))
            return
        DeckPreviewDialog(text, self.parent).exec()

    def write(self):
        analysis = self._analysis()
        if self._adapter(analysis) is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Write Input Deck",
            f"{analysis.name}.inp" if analysis else "model.inp",
            "Input deck (*.inp);;All files (*)",
        )
        if not path:
            return
        try:
            Path(path).write_text(self.deck_text(), encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(self.parent, "Deck export failed", str(exc))
            return
        self.store.message.emit(f"Wrote input deck {path}")

    def run(self):
        self.parent.controllers.analysis.run_active()

    def show_job(self, job_id):
        self.parent.controllers.jobs.open_monitor(job_id)

    def result_placeholder(self):
        self.parent.controllers.jobs.open_selected_results()
