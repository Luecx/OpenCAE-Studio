"""Controls Study execution delegation and saved topology-state display."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QInputDialog

from opencae.model.entities.optimization import OptimizationIteration, OptimizationRun
from opencae.optimization import (
    automatic_density_threshold,
    build_mesh_index,
    load_density_state,
)


class OptimizationRunMixin:
    """Delegate runs to JobManager and retain navigation for legacy run states."""

    def run(self):
        self.run_active()

    def run_active(self):
        study = self._optimization()
        if study is None:
            return self._need_optimization()
        self.jobs.run_study(study.id)

    def stop(self):
        self.jobs.stop_selected()

    def previous_iteration(self):
        self._step_iteration(-1)

    def next_iteration(self):
        self._step_iteration(1)

    def threshold(self):
        """Choose automatic constraint matching or a manual density cutoff."""
        value, accepted = QInputDialog.getDouble(
            self.parent,
            "Topology density threshold",
            "Show elements with density ≥ (0 = match constraint)",
            self._threshold if self._threshold is not None else 0.0,
            0.0,
            1.0,
            3,
        )
        if not accepted:
            return
        self._threshold = float(value) if value > 0.0 else None
        self._show_selected_iteration()

    def _show_selected_iteration(self):
        project = self.store.project
        selected = self.store.selection
        run = selected if isinstance(selected, OptimizationRun) else None
        iteration = selected if isinstance(selected, OptimizationIteration) else None
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
                (i for i, item in enumerate(run.iterations) if item.id == iteration.id),
                len(run.iterations) - 1,
            )
        self._display_iteration[run.id] = index
        density_path = Path(iteration.density_file)
        if not density_path.exists():
            self.store.message.emit(f"Density state is unavailable: {density_path}")
            return
        try:
            physical, volumes = load_density_state(density_path)
        except (OSError, KeyError, ValueError) as exc:
            self.store.message.emit(f"Density state could not be loaded: {exc}")
            return
        try:
            mesh_index = build_mesh_index(project)
        except Exception as exc:
            self.store.message.emit(str(exc))
            return
        if run.mesh_fingerprint and mesh_index.fingerprint != run.mesh_fingerprint:
            self.store.message.emit(
                "The mesh has changed since this Study job; its density field "
                "cannot be displayed safely"
            )
            return
        self.parent.ribbon.set_stage("STUDIES")
        self._show_density(run, iteration, mesh_index, physical, volumes)

    def _step_iteration(self, delta):
        project = self.store.project
        selected = self.store.selection
        run = selected if isinstance(selected, OptimizationRun) else None
        if isinstance(selected, OptimizationIteration):
            run = project.try_resolve(project.index.parent_id.get(selected.id))
        if not isinstance(run, OptimizationRun) or not run.iterations:
            study = self._optimization()
            run = study.runs[-1] if study and study.runs else None
        if not isinstance(run, OptimizationRun) or not run.iterations:
            return
        current = self._display_iteration.get(run.id, len(run.iterations) - 1)
        target = min(max(current + int(delta), 0), len(run.iterations) - 1)
        if target == current:
            return
        self._display_iteration[run.id] = target
        self.store.select(run.iterations[target])

    def stage_changed(self, stage):
        if stage != "STUDIES":
            self._pending_display = None
            self._overlay.clear(self.parent.viewport)
            self.parent.viewport.clear_region_previews("optimization-selection")
            self.parent.viewport.clear_datum_reference_preview()

    def _show_density(self, run, iteration, mesh_index, density, volumes=None):
        """Queue one density state and its optional exact element volumes."""
        viewport = self.parent.viewport
        if not hasattr(viewport, "scene") or not hasattr(viewport, "plotter"):
            return
        self._pending_display = (
            run,
            iteration,
            mesh_index,
            np.asarray(density, dtype=float).copy(),
            None if volumes is None else np.asarray(volumes, dtype=float).copy(),
        )
        if getattr(viewport, "display_mode", "") != "mesh":
            viewport.set_display_mode("mesh")
            QTimer.singleShot(0, self._restore_pending_display)
        else:
            self._restore_pending_display()

    def _restore_pending_display(self):
        """Restore the queued frame once the mesh viewport is ready."""
        if (
            self._pending_display is None
            or self.parent.ribbon.current_stage != "STUDIES"
        ):
            return
        run, iteration, mesh_index, density, volumes = self._pending_display
        try:
            threshold = self._threshold
            if threshold is None:
                matched = automatic_density_threshold(
                    self.store.project,
                    run,
                    mesh_index,
                    density,
                    volumes,
                )
                threshold = matched[0] if matched is not None else 0.0
            self._overlay.show(
                self.parent.viewport,
                run,
                iteration,
                mesh_index,
                density,
                threshold=threshold,
            )
        except Exception as exc:
            self.store.message.emit(f"Topology display failed: {exc}")
