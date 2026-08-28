"""Topology runner adapter for the central JobManager contract."""

from __future__ import annotations

from copy import deepcopy

import numpy as np
from PyQt6.QtCore import pyqtSignal

from opencae.model.entities.optimization import OptimizationIteration, OptimizationRun

from .runner import TopologyOptimizationRunner as _TopologyOptimizationRunner


class TopologyOptimizationRunner(_TopologyOptimizationRunner):
    """Expose topology completion as ``(status, message)`` without GUI hot paths.

    The generic iterative runner owns the numerical workflow. This JobManager-facing
    adapter keeps high-volume solver output, run metadata and completed iterations
    on lightweight runtime paths so a large persistent FE model is not repeatedly
    copied or re-indexed while the optimization is running.
    """

    finished = pyqtSignal(str, str)

    def _read_output(self):
        """Forward one QProcess read as one chunk instead of one signal per line."""
        if self.process is None:
            return
        text = bytes(self.process.readAllStandardOutput()).decode(errors="replace")
        if not text:
            return
        if self._log_stream is not None:
            self._log_stream.write(text)
            self._log_stream.flush()
        # JobManager already coalesces chunks before disk/monitor updates. Keeping
        # the original QProcess chunk here avoids thousands of Python/Qt signal
        # calls when FEMaster emits a large burst of line-oriented output.
        self.progress.emit(text)

    def _update_run(self, **changes):
        """Persist scalar OptimizationRun runtime state without document snapshots."""
        run = self.store.project.try_resolve(self.run_id)
        if not isinstance(run, OptimizationRun) or not changes:
            return
        self.store.update_runtime_fields(run.id, changes)

    def _append_iteration_runtime(self, iteration: OptimizationIteration):
        """Append one solver-produced iteration without rebuilding the whole Project.

        OptimizationIteration is a reference-free leaf Entity. We can therefore
        extend the already-valid ProjectIndex incrementally instead of routing this
        high-frequency runtime output through ProjectStore.execute(), whose rollback
        snapshot would deepcopy the complete FE model once per iteration.
        """
        project = self.store.project
        run = project.try_resolve(self.run_id)
        if not isinstance(run, OptimizationRun):
            raise ValueError("The topology optimization run no longer exists")
        if not isinstance(iteration, OptimizationIteration):
            raise TypeError("Topology runtime persistence requires an OptimizationIteration")

        index = project.index
        if iteration.id in index.by_id:
            raise ValueError(f"Optimization iteration '{iteration.id}' already exists")

        stored = deepcopy(iteration)
        position = len(run.iterations)
        run.iterations.append(stored)
        path = f"{index.path[run.id]}.iterations[{position}]"

        # Register only the new leaf. Existing ownership/reference data remains
        # valid because neither the run's identity nor any EntityRef changed.
        index.by_id[stored.id] = stored
        index.parent_id[stored.id] = run.id
        index.path[stored.id] = path
        stored._bind_project(project)

        # Preserve the observable model-update behavior for the Project/Solution
        # trees without creating an undo entry or a whole-document rollback copy.
        description = f"Completed topology iteration {stored.number}"
        self.store.runtime_changed.emit(run.id, ("iterations",))
        self.store.changed.emit(description)
        self.store.message.emit(description)
        return stored

    def _iteration_consumed(self, payload):
        """Commit a worker-computed iteration with only lightweight GUI-thread work."""
        self._consume_task = None
        if self.stopped or self._finished_state:
            return
        try:
            number = int(payload["number"])
            if number != self.iteration_number:
                raise RuntimeError("Stale topology result-processing result")
            iteration = self._append_iteration_runtime(payload["iteration"])
            calculation = payload["calculation"]
            self.iteration_ready.emit(
                self.run_id,
                iteration.id,
                self.index,
                np.asarray(payload["display_density"], dtype=float),
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

    def _finish(self, status, message):
        if self._finished_state:
            return
        self._finished_state = True
        if self._log_stream is not None:
            self._log_stream.close()
            self._log_stream = None
        self._update_run(status=status, message=str(message))
        self.progress.emit(str(message))
        self.finished.emit(str(status), str(message))
