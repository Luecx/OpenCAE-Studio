"""Own physical-beam presentation for editor scenes and self-contained FRD results."""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QProgressDialog

from opencae.geometry.cache import CACHE
from opencae.geometry.orphan_mesh import snapshot_from_part
from opencae.model.entities.elements import BeamElementDefinition
from opencae.results.beam_physical_model import beam_occurrences, part_beam_occurrences
from opencae.results.beam_physical_representation import (
    PHYSICAL_BEAM_CELL,
    build_beam_physical_representation_from_occurrences,
)
from opencae.results.frd_beam_metadata import beam_occurrences_from_frd
from .pyvista_mesh import add_physical_mesh, build_grid


class BeamPhysicalDisplayController:
    """Toggle beam visibility in results and generate editor-only beam overlays."""

    def __init__(self, viewport) -> None:
        self.viewport = viewport
        self.enabled = False
        self._bound = False
        self._last_options: dict = {}
        self._editor_actors = []

    def bind_toolbar(self) -> None:
        if self._bound:
            return
        self.viewport.toolbar.beam_physical_changed.connect(self.set_enabled)
        self.viewport.toolbar.display_changed.connect(self._display_changed)
        self._bound = True

    def sync_availability(self, *_args) -> None:
        if self.viewport.stage == "RESULTS":
            available = self._result_has_beams(
                getattr(self.viewport, "_active_result", None)
            )
        else:
            project = self._project()
            available = bool(
                project is not None and self._editor_has_beams(project)
            )
        self.viewport.toolbar.set_beam_available(available)

    def result_changed(self, result) -> None:
        available = self._result_has_beams(result)
        if self.viewport.stage == "RESULTS" and self.enabled and not available:
            self.enabled = False
            self.viewport.toolbar.set_beam_physical(False)
        self.viewport.toolbar.set_beam_available(available)

    def stage_changed(self, _stage=None) -> None:
        self._clear_editor_display(render=False)
        self.enabled = False
        self.viewport.toolbar.set_beam_physical(False)
        self.sync_availability()
        self.viewport.plotter.render()

    def model_changed(self, *_args) -> None:
        """Invalidate editor beam overlays after any authored model mutation."""
        if self.viewport.stage == "RESULTS":
            if getattr(self.viewport, "_active_result", None) is None and self.enabled:
                self.enabled = False
                self.viewport.toolbar.set_beam_physical(False)
            self.sync_availability()
            return
        if self.enabled:
            self._clear_editor_display(render=False)
            self.enabled = False
            self.viewport.toolbar.set_beam_physical(False)
            self.viewport.plotter.render()
        self.sync_availability()

    def set_enabled(self, enabled: bool) -> None:
        requested = bool(enabled)
        if self.viewport.stage == "RESULTS":
            self._set_result_enabled(requested)
        else:
            self._set_editor_enabled(requested)

    def prepare_options(self, result, field, options=None) -> dict:
        """Attach only the desired result subset; the loader owns beam expansion."""
        del field
        prepared = dict(options or {})
        self._last_options = dict(options or {})
        prepared["_physical_beams"] = bool(
            self.enabled
            and self.viewport.stage == "RESULTS"
            and self._result_has_beams(result)
        )
        return prepared

    def reset(self) -> None:
        self._clear_editor_display(render=False)
        self.enabled = False
        self._last_options = {}
        self.viewport.toolbar.set_beam_physical(False)
        self.viewport.toolbar.set_beam_available(False)

    def _set_result_enabled(self, requested: bool) -> None:
        result = getattr(self.viewport, "_active_result", None)
        if requested and result is None:
            self._reject("Open a solver result before enabling physical beams")
            return
        if requested and not self._result_has_beams(result):
            self._reject("This FRD contains no embedded OpenCAE beam metadata")
            return
        self.enabled = requested
        self.viewport.toolbar.set_beam_physical(requested)
        self._rerender_active()

    def _set_editor_enabled(self, requested: bool) -> None:
        if not requested:
            self._clear_editor_display(render=True)
            self.enabled = False
            self.viewport.toolbar.set_beam_physical(False)
            return
        try:
            grids = self._build_editor_grids(show_progress=True)
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            self._reject(str(exc))
            return
        self._clear_editor_display(render=False)
        for index, grid in enumerate(grids):
            actor = add_physical_mesh(
                self.viewport.plotter,
                grid,
                name=f"editor-physical-beams-{index}",
            )
            if actor is not None:
                self._editor_actors.append(actor)
        if not self._editor_actors:
            self._reject("No physical beam surfaces could be generated")
            return
        self.enabled = True
        self.viewport.toolbar.set_beam_physical(True)
        self.viewport.plotter.render()

    def _build_editor_grids(self, *, show_progress: bool):
        project = self._project()
        if project is None:
            raise ValueError("Physical beam rendering requires an active project")

        groups = []
        if self._assembly_stage(self.viewport.stage):
            occurrences = beam_occurrences(project)
            for instance in project.assembly.instances:
                if instance.suppressed:
                    continue
                part = project.try_resolve(instance.part_ref)
                if part is None:
                    continue
                owned = tuple(
                    occurrence
                    for occurrence in occurrences
                    if occurrence.instance_id == instance.id
                )
                if owned:
                    groups.append((part, instance, owned))
        else:
            part = self.viewport.store.active_part() if self.viewport.store else None
            owned = part_beam_occurrences(project, part)
            if part is not None and owned:
                groups.append((part, None, owned))

        if not groups:
            raise ValueError(
                "The current model has no beam elements with assigned profiles"
            )

        total = sum(len(owned) for _part, _instance, owned in groups)
        dialog = self._progress_dialog(total) if show_progress else None
        offset = 0
        grids = []
        try:
            for part, instance, owned in groups:
                source = self._editor_grid(part, instance)

                def progress(current, _local_total, label, *, base=offset):
                    if dialog is None:
                        return
                    dialog.setValue(min(total, base + int(current)))
                    dialog.setLabelText(str(label))
                    QApplication.processEvents()

                representation = build_beam_physical_representation_from_occurrences(
                    owned,
                    source,
                    progress=progress,
                    source_element_ids=True,
                )
                expanded = representation.expand(source)
                physical = np.asarray(
                    expanded.cell_data.get(
                        PHYSICAL_BEAM_CELL,
                        np.zeros(expanded.n_cells, dtype=np.uint8),
                    ),
                    dtype=bool,
                )
                indices = np.flatnonzero(physical)
                if len(indices):
                    grids.append(expanded.extract_cells(indices))
                offset += len(owned)
                if dialog is not None:
                    dialog.setValue(min(total, offset))
                    QApplication.processEvents()
            if dialog is not None:
                dialog.setValue(total)
                dialog.setLabelText("Finalizing beam representation")
                QApplication.processEvents()
        finally:
            if dialog is not None:
                dialog.close()
        if not grids:
            raise ValueError("No beam could be mapped to the current editor mesh")
        return tuple(grids)

    def _editor_grid(self, part, instance=None):
        snapshot = CACHE.mesh(part.id) or snapshot_from_part(part)
        if snapshot is None:
            raise ValueError(
                f"Generate a mesh for Part '{part.name}' before showing beams"
            )
        grid = build_grid(snapshot, instance, include_all_dimensions=True)
        if grid is None:
            raise ValueError(
                f"Part '{part.name}' has no renderable finite elements"
            )
        return grid

    def _clear_editor_display(self, *, render: bool) -> None:
        for actor in self._editor_actors:
            try:
                self.viewport.plotter.remove_actor(actor, render=False)
            except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
                pass
        self._editor_actors.clear()
        if render:
            self.viewport.plotter.render()

    def _display_changed(self, _mode) -> None:
        if self.viewport.stage == "RESULTS" or not self.enabled:
            return
        self._clear_editor_display(render=False)
        self.enabled = False
        self.viewport.toolbar.set_beam_physical(False)
        self.viewport.plotter.render()

    def _rerender_active(self) -> None:
        result = getattr(self.viewport, "_active_result", None)
        if result is None:
            return
        options = dict(self._last_options)
        options.pop("_animation", None)
        self.viewport.scene.show_result(
            result,
            getattr(self.viewport, "_active_result_field", None),
            options,
        )

    def _progress_dialog(self, total=0) -> QProgressDialog:
        maximum = max(0, int(total))
        dialog = QProgressDialog(
            "Generating beam profiles…",
            "",
            0,
            maximum,
            self.viewport,
        )
        dialog.setWindowTitle("Physical beams")
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.setCancelButton(None)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(False)
        dialog.setAutoReset(False)
        dialog.show()
        QApplication.processEvents()
        return dialog

    def _reject(self, message: str) -> None:
        self._clear_editor_display(render=False)
        self.enabled = False
        self.viewport.toolbar.set_beam_physical(False)
        self.viewport.message.emit(
            message or "Could not generate physical beams"
        )
        self.viewport.plotter.render()

    def _project(self):
        if self.viewport.stage == "RESULTS":
            return None
        return (
            self.viewport.store.project
            if self.viewport.store is not None
            else None
        )

    def _result_has_beams(self, result) -> bool:
        source = str(getattr(result, "source_file", "") or "")
        if not source.lower().endswith(".frd"):
            return False
        try:
            return bool(beam_occurrences_from_frd(source))
        except (OSError, RuntimeError, TypeError, ValueError):
            return False

    def _editor_has_beams(self, project) -> bool:
        if self._assembly_stage(self.viewport.stage):
            for instance in project.assembly.instances:
                if instance.suppressed:
                    continue
                part = project.try_resolve(instance.part_ref)
                if self._part_has_beams(part):
                    return True
            return False
        part = self.viewport.store.active_part() if self.viewport.store else None
        return self._part_has_beams(part)

    @staticmethod
    def _part_has_beams(part) -> bool:
        return bool(
            part is not None
            and part.section_assignments
            and any(
                isinstance(block.definition, BeamElementDefinition)
                and bool(block.connectivity)
                for block in part.mesh.element_blocks
            )
        )

    @staticmethod
    def _assembly_stage(stage) -> bool:
        return str(stage or "").upper() in {
            "ASSEMBLY",
            "CONSTRAINTS",
            "BOUNDARY CONDITIONS",
            "STEPS",
            "ANALYSIS",
            "STUDIES",
        }


def beam_physical_controller(viewport) -> BeamPhysicalDisplayController:
    controller = getattr(viewport, "_beam_physical_controller", None)
    if controller is None:
        controller = BeamPhysicalDisplayController(viewport)
        viewport._beam_physical_controller = controller
    controller.bind_toolbar()
    return controller
