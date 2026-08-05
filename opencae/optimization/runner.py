"""Runs the iterative FEMaster topology optimization process."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from time import monotonic

import numpy as np
from PyQt6.QtCore import QObject, QProcess, QThread, pyqtSignal, pyqtSlot

from opencae.model.entities.optimization import OptimizationIteration, OptimizationRun

from .deck import render_topology_deck
from .initialization_worker import TopologyInitializationWorker
from .iteration import compute_iteration, read_topology_fields
from .res_field_reader import ResFieldReader


class TopologyOptimizationRunner(QObject):
    """Coordinates filter initialization, FEMaster solves and OC updates."""

    progress = pyqtSignal(str)
    iteration_ready = pyqtSignal(object, object, object, object)
    finished = pyqtSignal(str, str)

    def __init__(
        self,
        store,
        project_snapshot,
        optimization_id: str,
        run_id: str,
        adapter,
        executable: str,
        extra_arguments: str,
        directory: str | Path,
        parent=None,
    ):
        super().__init__(parent)
        self.store = store
        self.project = deepcopy(project_snapshot)
        self.optimization_id = optimization_id
        self.run_id = run_id
        self.adapter = adapter
        self.executable = str(executable)
        self.extra_arguments = str(extra_arguments or "")
        self.directory = Path(directory)
        self.process: QProcess | None = None
        self.reader = ResFieldReader()
        self.stopped = False
        self._finished_state = False
        self.iteration_number = 0
        self.design_density = None
        self.physical_density = None
        self.previous_objective = None
        self.index = None
        self.masks = {}
        self.operators = None
        self._current_started = 0.0
        self._current_output_base: Path | None = None
        self._current_density_file: Path | None = None
        self._log_stream = None
        self._init_thread: QThread | None = None
        self._init_worker: TopologyInitializationWorker | None = None

    def start(self):
        optimization = self.project.try_resolve(self.optimization_id)
        if optimization is None:
            return self._fail("The topology optimization no longer exists")
        self.progress.emit(
            "Building topology mesh index and sparse filter operators…"
        )
        thread = QThread(self)
        worker = TopologyInitializationWorker(
            self.project,
            self.optimization_id,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.ready.connect(self._initialized)
        worker.failed.connect(self._fail)
        worker.done.connect(thread.quit)
        worker.done.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._initialization_thread_finished)
        self._init_thread = thread
        self._init_worker = worker
        thread.start()

    @pyqtSlot(object, object, object)
    def _initialized(self, index, masks, operators):
        if self.stopped or self._finished_state:
            return
        self.index = index
        self.masks = masks
        self.operators = operators
        optimization = self.project.resolve(self.optimization_id)
        controls = optimization.control_settings
        self.design_density = np.ones(self.index.count, dtype=float)
        design = self.masks["design"]
        self.design_density[design] = np.clip(
            controls.initial_density,
            controls.minimum_density,
            1.0,
        )
        self.design_density[self.masks["frozen_solid"]] = 1.0
        self.design_density[self.masks["frozen_void"]] = controls.minimum_density
        self.physical_density = self._physical(self.design_density)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._write_run_manifest(optimization, controls)
        self._update_run(
            status="Running",
            mesh_fingerprint=self.index.fingerprint,
            density_constraint_radius=self.operators.density_constraint_radius,
            sensitivity_radius=self.operators.sensitivity_radius,
            message="",
        )
        self.progress.emit(
            "Topology filters initialized: "
            f"density/constraint radius={self.operators.density_constraint_radius:.6g}, "
            f"sensitivity radius={self.operators.sensitivity_radius:.6g}"
        )
        try:
            self._launch_next()
        except Exception as exc:
            self._fail(str(exc))

    def _write_run_manifest(self, optimization, controls):
        data = {
            "optimization_id": optimization.id,
            "optimization_name": optimization.name,
            "mesh_fingerprint": self.index.fingerprint,
            "element_count": self.index.count,
            "minimum_element_distance": self.operators.minimum_distance,
            "density_constraint_radius": self.operators.density_constraint_radius,
            "sensitivity_radius": self.operators.sensitivity_radius,
            "controls": {
                "maximum_iterations": controls.maximum_iterations,
                "minimum_density": controls.minimum_density,
                "initial_density": controls.initial_density,
                "simp_exponent": controls.simp_exponent,
                "move_limit": controls.move_limit,
            },
        }
        (self.directory / "run.json").write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )

    def _initialization_thread_finished(self):
        self._init_thread = None
        self._init_worker = None

    def stop(self):
        self.stopped = True
        if (
            self.process is not None
            and self.process.state() != QProcess.ProcessState.NotRunning
        ):
            self.process.terminate()
            if not self.process.waitForFinished(1500):
                self.process.kill()
        self._finish("Cancelled", "Optimization cancelled by the user")

    def _launch_next(self):
        if self.stopped:
            return
        optimization = self.project.resolve(self.optimization_id)
        self.iteration_number += 1
        iteration_dir = self.directory / f"iteration-{self.iteration_number:04d}"
        iteration_dir.mkdir(parents=True, exist_ok=True)
        density_file = iteration_dir / "density.npz"
        np.savez_compressed(
            density_file,
            design=np.asarray(self.design_density, dtype=float),
            physical=np.asarray(self.physical_density, dtype=float),
            solver_ids=self.index.solver_ids,
            source_element_ids=self.index.source_element_ids,
            part_ids=np.asarray(self.index.part_ids),
            instance_ids=np.asarray(self.index.instance_ids),
        )
        deck_path = iteration_dir / "topology.inp"
        deck_path.write_text(
            render_topology_deck(
                self.project,
                optimization,
                self.index,
                self.physical_density,
            ),
            encoding="utf-8",
        )
        output_base = iteration_dir / "topology"
        command = self.adapter.build_command(
            self.executable,
            deck_path,
            output_base,
            self.extra_arguments,
        )
        self._current_output_base = output_base
        self._current_density_file = density_file
        self._current_started = monotonic()
        self._log_stream = (iteration_dir / "solver.log").open(
            "w",
            encoding="utf-8",
        )
        self.progress.emit(
            f"Topology iteration {self.iteration_number}: starting FEMaster"
        )
        process = QProcess(self)
        self.process = process
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.setWorkingDirectory(str(iteration_dir))
        process.readyReadStandardOutput.connect(self._read_output)
        process.finished.connect(self._process_finished)
        process.errorOccurred.connect(
            lambda error: self._fail(
                f"FEMaster process error: {error.name}"
            )
            if process.state() == QProcess.ProcessState.NotRunning
            else None
        )
        process.setProgram(command[0])
        process.setArguments(command[1:])
        process.start()

    def _read_output(self):
        if self.process is None:
            return
        text = bytes(self.process.readAllStandardOutput()).decode(errors="replace")
        if not text:
            return
        if self._log_stream is not None:
            self._log_stream.write(text)
            self._log_stream.flush()
        for line in text.splitlines():
            if line.strip():
                self.progress.emit(line.rstrip())

    def _process_finished(self, code, _status):
        process = self.process
        self._read_output()
        self.process = None
        if process is not None:
            process.deleteLater()
        if self._log_stream is not None:
            self._log_stream.close()
            self._log_stream = None
        if self.stopped:
            return
        if int(code) != 0:
            return self._fail(
                f"FEMaster failed in iteration {self.iteration_number} "
                f"with exit code {code}"
            )
        try:
            self._consume_iteration()
        except Exception as exc:
            self._fail(str(exc))

    def _consume_iteration(self):
        optimization = self.project.resolve(self.optimization_id)
        controls = optimization.control_settings
        result_path = self._current_output_base.with_suffix(".res")
        if not result_path.exists():
            raise FileNotFoundError(
                "FEMaster did not write the expected native result file "
                f"{result_path}"
            )
        fields = read_topology_fields(
            result_path,
            self.index,
            self.physical_density,
            self.reader,
        )
        calculation = compute_iteration(
            self.project,
            optimization,
            self.index,
            self.masks,
            self.operators,
            self.design_density,
            self.physical_density,
            self.previous_objective,
            fields,
        )
        terminal = bool(
            calculation.converged
            or self.iteration_number >= controls.maximum_iterations
        )
        keep = bool(
            controls.keep_solver_files
            and (
                self.iteration_number % controls.save_every == 0
                or terminal
            )
        )
        iteration = OptimizationIteration(
            name=f"Iteration-{self.iteration_number}",
            number=self.iteration_number,
            objective_value=calculation.objective_value,
            constraint_values={
                calculation.constraint_id: calculation.constraint_value
            },
            maximum_density_change=calculation.maximum_change,
            solver_time=max(monotonic() - self._current_started, 0.0),
            density_file=str(self._current_density_file),
            result_file=str(result_path) if keep else "",
            converged=calculation.converged,
        )
        self.store.add_entity(
            f"Completed topology iteration {self.iteration_number}",
            self.run_id,
            "iterations",
            iteration,
        )
        self.iteration_ready.emit(
            self.run_id,
            iteration.id,
            self.index,
            np.asarray(self.physical_density, dtype=float).copy(),
        )
        constraint = next(
            item for item in optimization.constraints if item.active
        )
        self._append_history(iteration, calculation, constraint)
        self.progress.emit(
            f"Iteration {self.iteration_number}: "
            f"objective={calculation.objective_value:.8g}, "
            f"constraint={calculation.constraint_value:.8g} <= {constraint.limit:.8g}, "
            f"max density change={calculation.maximum_change:.6g}"
        )
        if not keep:
            self._remove_solver_results(result_path)
        self.previous_objective = calculation.objective_value
        self.design_density = calculation.next_design_density
        self.physical_density = calculation.next_physical_density
        if calculation.converged:
            return self._finish(
                "Completed",
                f"Converged after {self.iteration_number} iterations",
            )
        if self.iteration_number >= controls.maximum_iterations:
            return self._finish(
                "Completed",
                f"Reached maximum iteration count ({controls.maximum_iterations})",
            )
        self._launch_next()

    def _append_history(self, iteration, calculation, constraint):
        row = {
            "iteration": self.iteration_number,
            "objective": calculation.objective_value,
            "constraint": calculation.constraint_value,
            "constraint_limit": constraint.limit,
            "maximum_density_change": calculation.maximum_change,
            "solver_time": iteration.solver_time,
            "converged": calculation.converged,
            "density_file": str(self._current_density_file),
        }
        with (self.directory / "history.jsonl").open(
            "a",
            encoding="utf-8",
        ) as history:
            history.write(json.dumps(row) + "\n")

    def _remove_solver_results(self, result_path):
        try:
            result_path.unlink(missing_ok=True)
            self._current_output_base.with_suffix(".frd").unlink(missing_ok=True)
        except OSError:
            pass

    def _physical(self, design_density):
        optimization = self.project.resolve(self.optimization_id)
        controls = optimization.control_settings
        physical = self.operators.physical_density(
            np.asarray(design_density, dtype=float)
        )
        physical = np.clip(physical, controls.minimum_density, 1.0)
        physical[~self.masks["design"]] = 1.0
        physical[self.masks["frozen_solid"]] = 1.0
        physical[self.masks["frozen_void"]] = controls.minimum_density
        return physical

    def _update_run(self, **changes):
        project = self.store.project
        run = project.try_resolve(self.run_id)
        if not isinstance(run, OptimizationRun):
            return
        candidate = deepcopy(run)
        for key, value in changes.items():
            setattr(candidate, key, value)
        parent_id = project.index.parent_id.get(run.id)
        if parent_id:
            self.store.replace_entity(
                f"Updated optimization run {run.name}",
                parent_id,
                "runs",
                candidate,
            )

    def _fail(self, message):
        self._finish("Failed", str(message))

    def _finish(self, status, message):
        if self._finished_state:
            return
        self._finished_state = True
        if self._log_stream is not None:
            self._log_stream.close()
            self._log_stream = None
        self._update_run(status=status, message=str(message))
        self.progress.emit(str(message))
        self.finished.emit(self.run_id, status)
