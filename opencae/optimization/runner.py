"""Runs the iterative FEMaster topology optimization process."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from time import monotonic

import numpy as np
from PyQt6.QtCore import QObject, QProcess, QThread, QTimer, pyqtSignal, pyqtSlot

from opencae.controllers.background_task import BackgroundTask
from opencae.model.entities.optimization import OptimizationIteration, OptimizationRun

from .deck import render_topology_deck
from .density_state import store_density_volumes
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
        # JobManager already provides a stable deepcopy. Avoid another expensive
        # graph copy in the GUI thread when constructing the runner.
        self.project = project_snapshot
        self.optimization_id = optimization_id
        self.run_id = run_id
        self.adapter = adapter
        self.executable = str(executable)
        self.extra_arguments = str(extra_arguments or "")
        self.directory = Path(directory)
        self.process: QProcess | None = None
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
        self._launch_task: BackgroundTask | None = None
        self._consume_task: BackgroundTask | None = None

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
        self._launch_next()

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
        """Cancel promptly without blocking Qt while a child process exits."""
        if self._finished_state:
            return
        self.stopped = True
        process = self.process
        if (
            process is not None
            and process.state() != QProcess.ProcessState.NotRunning
        ):
            process.terminate()
            QTimer.singleShot(1500, self._kill_if_running)
        self._finish("Cancelled", "Optimization cancelled by the user")

    def _kill_if_running(self):
        process = self.process
        if (
            self.stopped
            and process is not None
            and process.state() != QProcess.ProcessState.NotRunning
        ):
            process.kill()

    def _launch_next(self):
        """Prepare the next density file and solver deck on a worker thread."""
        if self.stopped or self._finished_state or self._launch_task is not None:
            return
        self.iteration_number += 1
        number = self.iteration_number
        design = np.asarray(self.design_density, dtype=float).copy()
        physical = np.asarray(self.physical_density, dtype=float).copy()
        self.progress.emit(f"Topology iteration {number}: preparing solver input…")
        task = BackgroundTask(
            lambda: self._prepare_iteration(number, design, physical),
            on_result=self._iteration_prepared,
            on_error=self._launch_failed,
            parent=self,
        )
        self._launch_task = task
        task.start()

    def _prepare_iteration(self, number, design_density, physical_density):
        """Write one iteration's compressed density state and deck off-thread."""
        optimization = self.project.resolve(self.optimization_id)
        iteration_dir = self.directory / f"iteration-{number:04d}"
        iteration_dir.mkdir(parents=True, exist_ok=True)
        density_file = iteration_dir / "density.npz"
        np.savez_compressed(
            density_file,
            design=design_density,
            physical=physical_density,
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
                physical_density,
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
        if not command:
            raise ValueError("The solver adapter produced an empty command")
        return {
            "number": number,
            "iteration_dir": iteration_dir,
            "density_file": density_file,
            "output_base": output_base,
            "command": tuple(str(value) for value in command),
        }

    def _iteration_prepared(self, payload):
        self._launch_task = None
        if self.stopped or self._finished_state:
            return
        try:
            if int(payload["number"]) != self.iteration_number:
                raise RuntimeError("Stale topology iteration preparation result")
            iteration_dir = Path(payload["iteration_dir"])
            self._current_output_base = Path(payload["output_base"])
            self._current_density_file = Path(payload["density_file"])
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
            process.errorOccurred.connect(self._process_error)
            command = payload["command"]
            process.setProgram(command[0])
            process.setArguments(list(command[1:]))
            process.start()
        except Exception as exc:
            self._fail(str(exc))

    def _launch_failed(self, error):
        self._launch_task = None
        if not self.stopped and not self._finished_state:
            self._fail(str(error))

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

    def _process_error(self, error):
        process = self.process
        if process is None or self.stopped or self._finished_state:
            return
        if process.state() == QProcess.ProcessState.NotRunning:
            self.process = None
            process.deleteLater()
            self._fail(f"FEMaster process error: {error.name}")

    def _process_finished(self, code, _status):
        process = self.process
        self._read_output()
        self.process = None
        if process is not None:
            process.deleteLater()
        if self._log_stream is not None:
            self._log_stream.close()
            self._log_stream = None
        if self.stopped or self._finished_state:
            return
        if int(code) != 0:
            return self._fail(
                f"FEMaster failed in iteration {self.iteration_number} "
                f"with exit code {code}"
            )
        self._start_result_processing()

    def _start_result_processing(self):
        """Parse solver output and compute OC updates away from the GUI thread."""
        if self._consume_task is not None or self._current_output_base is None:
            return
        number = self.iteration_number
        output_base = Path(self._current_output_base)
        density_file = Path(self._current_density_file)
        started = float(self._current_started)
        design = np.asarray(self.design_density, dtype=float).copy()
        physical = np.asarray(self.physical_density, dtype=float).copy()
        previous = self.previous_objective
        self.progress.emit(f"Topology iteration {number}: processing results…")
        task = BackgroundTask(
            lambda: self._compute_iteration_payload(
                number,
                output_base,
                density_file,
                started,
                design,
                physical,
                previous,
            ),
            on_result=self._iteration_consumed,
            on_error=self._consume_failed,
            parent=self,
        )
        self._consume_task = task
        task.start()

    def _compute_iteration_payload(
        self,
        number,
        output_base,
        density_file,
        started,
        design_density,
        physical_density,
        previous_objective,
    ):
        """Read fields, run sensitivities/OC, and perform iteration file I/O off-thread."""
        optimization = self.project.resolve(self.optimization_id)
        controls = optimization.control_settings
        result_path = output_base.with_suffix(".res")
        if not result_path.exists():
            raise FileNotFoundError(
                "FEMaster did not write the expected native result file "
                f"{result_path}"
            )
        fields = read_topology_fields(
            result_path,
            self.index,
            physical_density,
            ResFieldReader(),
        )
        store_density_volumes(density_file, fields["VOLUME"])
        calculation = compute_iteration(
            self.project,
            optimization,
            self.index,
            self.masks,
            self.operators,
            design_density,
            physical_density,
            previous_objective,
            fields,
        )
        terminal = bool(
            calculation.converged
            or number >= controls.maximum_iterations
        )
        keep = bool(
            controls.keep_solver_files
            and (number % controls.save_every == 0 or terminal)
        )
        iteration = OptimizationIteration(
            name=f"Iteration-{number}",
            number=number,
            objective_value=calculation.objective_value,
            constraint_values={
                calculation.constraint_id: calculation.constraint_value
            },
            maximum_density_change=calculation.maximum_change,
            solver_time=max(monotonic() - started, 0.0),
            density_file=str(density_file),
            result_file=str(result_path) if keep else "",
            converged=calculation.converged,
        )
        constraint = next(item for item in optimization.constraints if item.active)
        row = {
            "iteration": number,
            "objective": calculation.objective_value,
            "constraint": calculation.constraint_value,
            "constraint_limit": constraint.limit,
            "maximum_density_change": calculation.maximum_change,
            "solver_time": iteration.solver_time,
            "converged": calculation.converged,
            "density_file": str(density_file),
        }
        with (self.directory / "history.jsonl").open(
            "a",
            encoding="utf-8",
        ) as history:
            history.write(json.dumps(row) + "\n")
        if not keep:
            try:
                result_path.unlink(missing_ok=True)
                output_base.with_suffix(".frd").unlink(missing_ok=True)
            except OSError:
                pass
        return {
            "number": number,
            "iteration": iteration,
            "calculation": calculation,
            "constraint_limit": float(constraint.limit),
            "display_density": physical_density,
            "maximum_iterations": int(controls.maximum_iterations),
        }

    def _iteration_consumed(self, payload):
        self._consume_task = None
        if self.stopped or self._finished_state:
            return
        try:
            number = int(payload["number"])
            if number != self.iteration_number:
                raise RuntimeError("Stale topology result-processing result")
            iteration = payload["iteration"]
            calculation = payload["calculation"]
            self.store.add_entity(
                f"Completed topology iteration {number}",
                self.run_id,
                "iterations",
                iteration,
            )
            self.iteration_ready.emit(
                self.run_id,
                iteration.id,
                self.index,
                np.asarray(payload["display_density"], dtype=float).copy(),
            )
            self.progress.emit(
                f"Iteration {number}: "
                f"objective={calculation.objective_value:.8g}, "
                f"constraint={calculation.constraint_value:.8g} <= "
                f"{payload['constraint_limit']:.8g}, "
                f"max density change={calculation.maximum_change:.6g}"
            )
            self.previous_objective = calculation.objective_value
            self.design_density = calculation.next_design_density
            self.physical_density = calculation.next_physical_density
            if calculation.converged:
                return self._finish(
                    "Completed",
                    f"Converged after {number} iterations",
                )
            if number >= int(payload["maximum_iterations"]):
                return self._finish(
                    "Completed",
                    f"Reached maximum iteration count ({payload['maximum_iterations']})",
                )
            self._launch_next()
        except Exception as exc:
            self._fail(str(exc))

    def _consume_failed(self, error):
        self._consume_task = None
        if not self.stopped and not self._finished_state:
            self._fail(str(error))

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
