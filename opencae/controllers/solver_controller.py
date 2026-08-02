from __future__ import annotations
from pathlib import Path
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from opencae.model.entities.jobs import Job, ResultSet
from opencae.ui.dialogs.deck_preview import DeckPreviewDialog
from opencae.ui.dialogs.solver_run import SolverRunDialog
from opencae.ui.dialogs.job_settings import JobSettingsDialog
from PyQt6.QtWidgets import QDialog
from opencae.results import FrdLoader
class SolverController:
    def __init__(self, store, parent, settings, solvers):
        self.store = store; self.parent = parent; self.settings = settings; self.solvers = solvers; self._runs = {}; self._results = FrdLoader()
    def _analysis(self):
        from opencae.model.entities.analysis import Analysis, AnalysisStep
        selected = self.store.selection
        if isinstance(selected, Analysis): return selected
        if isinstance(selected, AnalysisStep):
            return next((analysis for analysis in self.store.project.analyses if selected in analysis.steps), None)
        return self.store.project.analyses[0] if self.store.project.analyses else None
    def _adapter(self):
        return self.solvers.get(self.settings.selected_solver)
    def deck_text(self):
        adapter = self._adapter(); analysis = self._analysis()
        if adapter is None: raise ValueError("Select an enabled solver first")
        if analysis is None: raise ValueError("Define an analysis first")
        if not any(not item.suppressed for item in self.store.project.assembly.instances):
            raise ValueError("Create at least one assembly instance before exporting or running an analysis")
        return adapter.write_deck_text(self.store.project, None)
    def validate(self):
        try:
            text = self.deck_text()
        except Exception as exc:
            QMessageBox.warning(self.parent, "Validation failed", str(exc))
            return
        self.store.message.emit(f"Deck validation passed ({len(text.splitlines())} lines)")
    def preview(self):
        try: text = self.deck_text()
        except Exception as exc: QMessageBox.warning(self.parent, "Deck unavailable", str(exc)); return
        DeckPreviewDialog(text, self.parent).exec()
    def write(self):
        if self._adapter() is None: return
        path, _ = QFileDialog.getSaveFileName(self.parent, "Write Input Deck", "model.inp", "Input deck (*.inp);;All files (*)")
        if path:
            try: Path(path).write_text(self.deck_text(), encoding="utf-8")
            except Exception as exc: QMessageBox.critical(self.parent, "Deck export failed", str(exc)); return
            self.store.message.emit(f"Wrote input deck {path}")
    def run(self):
        adapter = self._adapter(); config = self.settings.solver_config(self.settings.selected_solver)
        if adapter is None: return
        executable = str(config.get("executable", ""))
        if not Path(executable).is_file(): QMessageBox.warning(self.parent, "Solver unavailable", "The configured executable does not exist."); return
        try: deck = self.deck_text()
        except Exception as exc: QMessageBox.critical(self.parent, "Validation failed", str(exc)); return
        options = JobSettingsDialog(adapter.name, str(config.get("extra_arguments", "")), self.parent)
        if options.exec() != QDialog.DialogCode.Accepted: return
        run_options = options.values(); analysis = self._analysis(); job_name = f"Job-{len(self.store.project.jobs) + 1}"
        root = Path(self.settings.working_directory or (self.store.project.path.parent if self.store.project.path else Path.cwd()))
        directory = root / job_name; directory.mkdir(parents=True, exist_ok=True)
        deck_path = directory / f"{job_name}.inp"; deck_path.write_text(deck, encoding="utf-8")
        output_base = directory / job_name
        job = Job(name=job_name, analysis_name="All Steps", solver=adapter.name, status="Running", input_deck=str(deck_path), settings=dict(run_options))
        self.store.mutate(f"Started {job_name}", lambda project: project.jobs.append(job))
        extra = run_options["extra_arguments"]
        if adapter.name == "FEMaster": extra = f"--ncpus {run_options['threads']} {extra}".strip()
        command = adapter.build_command(executable, deck_path, output_base, extra)
        dialog = SolverRunDialog(f"{job_name} — {adapter.name}", command, directory, self.parent)
        dialog.completed.connect(lambda code, d=dialog: self._finished(job, adapter, output_base, code, d))
        self._runs[job.name] = dialog; dialog.show()
    def _finished(self, job, adapter, output_base, code, dialog):
        job.status = "Completed" if code == 0 else f"Failed ({code})"
        source = next((path for path in adapter.result_candidates(output_base) if path.exists()), None)
        if source and source.suffix.lower() == ".frd":
            try: fields = self._results.fields(source)
            except Exception as exc:
                fields = []; dialog.output.appendPlainText(f"Result metadata could not be read: {exc}")
            step_names=[step.name for analysis in self.store.project.analyses for step in analysis.steps]
            result = ResultSet(name=job.name, job_name=job.name, source_file=str(source), status="Available", fields=fields, metadata={"step_names":step_names})
            self.store.project.results.append(result)
        self.store.changed.emit(f"Finished {job.name}")
        self.store.message.emit(job.status)
    def show_job(self, job_name):
        dialog = self._runs.get(job_name)
        if dialog is not None: dialog.reopen()
        else: self.store.message.emit(f"No live console is available for {job_name}")
    def result_placeholder(self):
        self.parent.ribbon.set_stage("RESULTS")
