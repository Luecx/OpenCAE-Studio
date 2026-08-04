from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QInputDialog, QMessageBox

from opencae.model.core import EntityRef
from opencae.model.entities.optimization import (
    OptimizationIteration,
    OptimizationRun,
)
from opencae.optimization import build_mesh_index, validate_topology_optimization
from opencae.optimization.runner import TopologyOptimizationRunner
from opencae.ui.dialogs.topology_run import TopologyRunDialog


class OptimizationRunMixin:
    def run(self):
        optimization = self._optimization()
        if optimization is None:
            return self._need_optimization()
        adapter = self.solvers.get("FEMaster")
        config = self.settings.solver_config("FEMaster")
        executable = str(config.get("executable", ""))
        if (
            adapter is None
            or "FEMaster" not in self.settings.enabled_solvers()
            or not Path(executable).is_file()
        ):
            QMessageBox.warning(
                self.parent,
                "FEMaster unavailable",
                "Configure a valid FEMaster executable before running topology optimization.",
            )
            return
        errors, _index, _masks, _operators = validate_topology_optimization(
            self.store.project, optimization, build_operators=True
        )
        if errors:
            QMessageBox.warning(
                self.parent,
                "Topology validation failed",
                "\n".join(f"• {item}" for item in errors),
            )
            return

        root = Path(
            self.settings.working_directory
            or (
                self.store.project.path.parent
                if self.store.project.path
                else Path.cwd()
            )
        )
        run_name = f"Optimization Run-{len(optimization.runs) + 1}"
        run = OptimizationRun(
            name=run_name,
            optimization_ref=EntityRef.of(
                optimization, "TopologyOptimization"
            ),
            status="Prepared",
        )
        safe_name = "".join(
            character if character.isalnum() or character in "-_" else "_"
            for character in optimization.name
        )
        directory = root / f"{safe_name}-{run.id[-8:]}"
        run.directory = str(directory)
        self.store.add_entity(
            f"Started {run_name}", optimization.id, "runs", run
        )
        project_snapshot = deepcopy(self.store.project)
        runner = TopologyOptimizationRunner(
            self.store,
            project_snapshot,
            optimization.id,
            run.id,
            adapter,
            executable,
            str(config.get("extra_arguments", "")),
            directory,
            self.parent,
        )
        console = TopologyRunDialog(run_name, directory, self.parent)
        console.stop_requested.connect(runner.stop)
        runner.progress.connect(self.store.message.emit)
        runner.progress.connect(console.append)
        runner.iteration_ready.connect(self._iteration_ready)
        runner.finished.connect(self._run_finished)
        runner.finished.connect(
            lambda _rid, status, dialog=console: dialog.complete(status)
        )
        self._runners[run.id] = runner
        self._run_dialogs[run.id] = console
        self.parent.ribbon.set_stage("OPTIMIZATION")
        console.show()
        self.parent.refresh_action_states()
        runner.start()

    def stop(self):
        optimization = self._optimization()
        candidates = []
        if optimization is not None:
            candidates = [
                run.id for run in optimization.runs if run.id in self._runners
            ]
        if not candidates:
            candidates = list(self._runners)
        if not candidates:
            self.store.message.emit(
                "No topology optimization is currently running"
            )
            return
        self._runners[candidates[-1]].stop()

    def previous_iteration(self):
        self._step_iteration(-1)

    def next_iteration(self):
        self._step_iteration(1)

    def threshold(self):
        value, accepted = QInputDialog.getDouble(
            self.parent,
            "Topology density threshold",
            "Show elements with density ≥",
            self._threshold,
            0.0,
            1.0,
            3,
        )
        if not accepted:
            return
        self._threshold = float(value)
        self._show_selected_iteration()

    def _show_selected_iteration(self):
        project = self.store.project
        selected = self.store.selection
        run = selected if isinstance(selected, OptimizationRun) else None
        iteration = (
            selected if isinstance(selected, OptimizationIteration) else None
        )
        if iteration is not None:
            run = project.try_resolve(project.index.parent_id.get(iteration.id))
        if not isinstance(run, OptimizationRun) or not run.iterations:
            return
        if iteration is None:
            index = self._display_iteration.get(run.id, len(run.iterations) - 1)
            index = min(max(index, 0), len(run.iterations) - 1)
            iteration = run.iterations[index]
        else:
            index = next(
                (
                    i
                    for i, item in enumerate(run.iterations)
                    if item.id == iteration.id
                ),
                len(run.iterations) - 1,
            )
        self._display_iteration[run.id] = index
        density_path = Path(iteration.density_file)
        if not density_path.exists():
            self.store.message.emit(
                f"Density state is unavailable: {density_path}"
            )
            return
        with np.load(density_path, allow_pickle=False) as values:
            physical = np.asarray(values["physical"], dtype=float).copy()
        try:
            mesh_index = build_mesh_index(project)
        except Exception as exc:
            self.store.message.emit(str(exc))
            return
        if (
            run.mesh_fingerprint
            and mesh_index.fingerprint != run.mesh_fingerprint
        ):
            self.store.message.emit(
                "The mesh has changed since this topology run; its density "
                "field cannot be displayed safely"
            )
            return
        self.parent.ribbon.set_stage("OPTIMIZATION")
        self._show_density(run, iteration, mesh_index, physical)

    def _step_iteration(self, delta):
        project = self.store.project
        selected = self.store.selection
        run = selected if isinstance(selected, OptimizationRun) else None
        if isinstance(selected, OptimizationIteration):
            run = project.try_resolve(project.index.parent_id.get(selected.id))
        if not isinstance(run, OptimizationRun) or not run.iterations:
            optimization = self._optimization()
            run = (
                optimization.runs[-1]
                if optimization and optimization.runs
                else None
            )
        if not isinstance(run, OptimizationRun) or not run.iterations:
            return
        current = self._display_iteration.get(run.id, len(run.iterations) - 1)
        target = min(max(current + int(delta), 0), len(run.iterations) - 1)
        if target == current:
            return
        self._display_iteration[run.id] = target
        self.store.select(run.iterations[target])

    def _iteration_ready(self, run_id, iteration_id, mesh_index, density):
        run = self.store.project.try_resolve(run_id)
        iteration = self.store.project.try_resolve(iteration_id)
        if not isinstance(run, OptimizationRun) or not isinstance(
            iteration, OptimizationIteration
        ):
            return
        self._display_iteration[run.id] = len(run.iterations) - 1
        self._show_density(run, iteration, mesh_index, density)

    def _run_finished(self, run_id, _status):
        self._runners.pop(run_id, None)
        try:
            self.parent.refresh_action_states()
        except (AttributeError, RuntimeError):
            pass

    def stage_changed(self, stage):
        if stage != "OPTIMIZATION":
            self._pending_display = None
            self._overlay.clear(self.parent.viewport)
            self.parent.viewport.clear_region_previews("optimization-selection")
            self.parent.viewport.clear_datum_reference_preview()

    def _show_density(self, run, iteration, mesh_index, density):
        viewport = self.parent.viewport
        if not hasattr(viewport, "scene") or not hasattr(viewport, "plotter"):
            return
        self._pending_display = (
            run,
            iteration,
            mesh_index,
            np.asarray(density, dtype=float).copy(),
        )
        if getattr(viewport, "display_mode", "") != "mesh":
            viewport.set_display_mode("mesh")
            QTimer.singleShot(0, self._restore_pending_display)
        else:
            self._restore_pending_display()

    def _restore_pending_display(self):
        if (
            self._pending_display is None
            or self.parent.ribbon.current_stage != "OPTIMIZATION"
        ):
            return
        run, iteration, mesh_index, density = self._pending_display
        try:
            self._overlay.show(
                self.parent.viewport,
                run,
                iteration,
                mesh_index,
                density,
                threshold=self._threshold,
            )
        except Exception as exc:
            self.store.message.emit(f"Topology display failed: {exc}")
