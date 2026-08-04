from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox

from opencae.model.core import EntityRef
from opencae.model.entities.jobs import Job, ResultSet
from opencae.results import FrdLoader
from opencae.store.commands import CompositeCommand, make_add_command, make_replace_command
from opencae.ui.dialogs.deck_preview import DeckPreviewDialog
from opencae.ui.dialogs.job_settings import JobSettingsDialog
from opencae.ui.dialogs.solver_run import SolverRunDialog


class SolverController:
    def __init__(self, store, parent, settings, solvers):
        self.store = store
        self.parent = parent
        self.settings = settings
        self.solvers = solvers
        self._runs = {}
        self._results = FrdLoader()

    def _analysis(self):
        from opencae.model.entities.analysis import Analysis, AnalysisStep

        project = self.store.project
        selected = self.store.selection
        if isinstance(selected, Analysis):
            current = project.try_resolve(selected.id)
            return current if isinstance(current, Analysis) else None
        if isinstance(selected, AnalysisStep):
            return next(
                (
                    analysis
                    for analysis in project.analyses
                    if any(step.id == selected.id for step in analysis.steps)
                ),
                None,
            )
        return project.analyses[0] if project.analyses else None

    def _adapter(self):
        return self.solvers.get(self.settings.selected_solver)

    def deck_text(self):
        adapter = self._adapter()
        analysis = self._analysis()
        if adapter is None:
            raise ValueError("Select an enabled solver first")
        if analysis is None:
            raise ValueError("Define an analysis first")
        if not any(not item.suppressed for item in self.store.project.assembly.instances):
            raise ValueError("Create at least one assembly instance before exporting or running an analysis")
        return adapter.write_deck_text(self.store.project, analysis)

    def validate(self):
        try:
            text = self.deck_text()
        except Exception as exc:
            QMessageBox.warning(self.parent, "Validation failed", str(exc))
            return
        self.store.message.emit(f"Deck validation passed ({len(text.splitlines())} lines)")

    def preview(self):
        try:
            text = self.deck_text()
        except Exception as exc:
            QMessageBox.warning(self.parent, "Deck unavailable", str(exc))
            return
        DeckPreviewDialog(text, self.parent).exec()

    def write(self):
        if self._adapter() is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Write Input Deck",
            "model.inp",
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
        adapter = self._adapter()
        config = self.settings.solver_config(self.settings.selected_solver)
        if adapter is None:
            return
        executable = str(config.get("executable", ""))
        if not Path(executable).is_file():
            QMessageBox.warning(
                self.parent,
                "Solver unavailable",
                "The configured executable does not exist.",
            )
            return
        try:
            deck = self.deck_text()
        except Exception as exc:
            QMessageBox.critical(self.parent, "Validation failed", str(exc))
            return
        options = JobSettingsDialog(
            adapter.name,
            str(config.get("extra_arguments", "")),
            self.parent,
        )
        if options.exec() != QDialog.DialogCode.Accepted:
            return
        run_options = options.values()
        analysis = self._analysis()
        job_name = f"Job-{len(self.store.project.jobs) + 1}"
        root = Path(
            self.settings.working_directory
            or (
                self.store.project.path.parent
                if self.store.project.path
                else Path.cwd()
            )
        )
        directory = root / job_name
        directory.mkdir(parents=True, exist_ok=True)
        deck_path = directory / f"{job_name}.inp"
        deck_path.write_text(deck, encoding="utf-8")
        output_base = directory / job_name
        job = Job(
            name=job_name,
            analysis_ref=EntityRef.of(analysis, "Analysis"),
            solver=adapter.name,
            status="Running",
            input_deck=str(deck_path),
            settings=dict(run_options),
        )
        self.store.add_entity(f"Started {job_name}", self.store.project.id, "jobs", job)
        extra = run_options["extra_arguments"]
        if adapter.name == "FEMaster":
            extra = f"--ncpus {run_options['threads']} {extra}".strip()
        command = adapter.build_command(executable, deck_path, output_base, extra)
        dialog = SolverRunDialog(
            f"{job_name} — {adapter.name}",
            command,
            directory,
            self.parent,
        )
        dialog.completed.connect(
            lambda code, d=dialog, jid=job.id: self._finished(
                jid,
                adapter,
                output_base,
                code,
                d,
            )
        )
        self._runs[job.name] = dialog
        dialog.show()

    def _finished(self, job_id, adapter, output_base, code, dialog):
        project = self.store.project
        stored_job = project.try_resolve(job_id)
        if stored_job is None:
            return
        status = "Completed" if code == 0 else f"Failed ({code})"
        source = next(
            (path for path in adapter.result_candidates(output_base) if path.exists()),
            None,
        )
        fields = []
        if source and source.suffix.lower() == ".frd":
            try:
                fields = self._results.fields(source)
            except Exception as exc:
                dialog.output.appendPlainText(f"Result metadata could not be read: {exc}")

        replacement_job = deepcopy(stored_job)
        replacement_job.status = status
        commands = [make_replace_command(project, project.id, "jobs", replacement_job)]
        if source and source.suffix.lower() == ".frd":
            step_names = [
                step.name
                for analysis in project.analyses
                for step in analysis.steps
            ]
            previous = next(
                (
                    item
                    for item in project.results
                    if item.job_ref and item.job_ref.entity_id == stored_job.id
                ),
                None,
            )
            kwargs = dict(
                name=stored_job.name,
                job_ref=EntityRef.of(stored_job, "Job"),
                source_file=str(source),
                status="Available",
                fields=fields,
                metadata={"step_names": step_names},
            )
            result = ResultSet(id=previous.id, **kwargs) if previous else ResultSet(**kwargs)
            commands.append(
                make_replace_command(project, project.id, "results", result)
                if previous
                else make_add_command(project, project.id, "results", result)
            )
        self.store.execute(
            f"Finished {stored_job.name}",
            CompositeCommand(tuple(commands)),
        )
        self.store.message.emit(status)

    def show_job(self, job_name):
        dialog = self._runs.get(job_name)
        if dialog is not None:
            dialog.reopen()
        else:
            self.store.message.emit(f"No live console is available for {job_name}")

    def result_placeholder(self):
        self.parent.ribbon.set_stage("RESULTS")
