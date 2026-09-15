"""Own physical-beam generation for editor scenes and stored solver results."""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QProgressDialog

from opencae.geometry.cache import CACHE
from opencae.geometry.orphan_mesh import snapshot_from_part
from opencae.model.entities.elements import BeamElementDefinition
from opencae.results import FrdLoader
from opencae.results.beam_physical_model import (
    beam_occurrences,
    part_beam_occurrences,
)
from opencae.results.beam_physical_representation import (
    build_beam_physical_representation,
    build_beam_physical_representation_from_occurrences,
)
from opencae.results.femaster_res_section_forces import (
    load_local_section_forces,
)
from .pyvista_mesh import add_physical_mesh, build_grid


class BeamPhysicalDisplayController:
    """Render physical beams freshly in editors and cached in stored results."""

    def __init__(self, viewport) -> None:
        self.viewport = viewport
        self.enabled = False
        self._bound = False
        self._loader = FrdLoader()
        self._representations = {}
        self._section_forces = {}
        self._last_options: dict = {}
        self._editor_actors = []

    def bind_toolbar(self) -> None:
        """Connect shared viewport controls exactly once."""
        if self._bound:
            return
        self.viewport.toolbar.beam_physical_changed.connect(self.set_enabled)
        self.viewport.toolbar.display_changed.connect(self._display_changed)
        self._bound = True

    def sync_availability(self, *_args) -> None:
        """Enable Beam whenever the current model/result context can contain beams."""
        project = self._project()
        if project is None:
            self.viewport.toolbar.set_beam_available(False)
            return
        if self.viewport.stage == "RESULTS":
            result = getattr(self.viewport, "_active_result", None)
            available = bool(
                result is not None
                and getattr(result, "source_file", "")
                and self._project_has_beams(project)
            )
        else:
            available = self._editor_has_beams(project)
        self.viewport.toolbar.set_beam_available(available)

    def result_changed(self, result) -> None:
        """Update availability when the active stored result changes."""
        project = self._project()
        available = bool(
            project is not None
            and result is not None
            and getattr(result, "source_file", "")
            and self._project_has_beams(project)
        )
        self.viewport.toolbar.set_beam_available(available)

    def stage_changed(self, _stage=None) -> None:
        """Drop transient editor surfaces when the viewport context changes."""
        self._clear_editor_display(render=False)
        self.enabled = False
        self.viewport.toolbar.set_beam_physical(False)
        self.sync_availability()
        self.viewport.plotter.render()

    def model_changed(self, *_args) -> None:
        """Never retain stale editor surfaces after a model/active-Part change."""
        if self.viewport.stage != "RESULTS" and self.enabled:
            self._clear_editor_display(render=False)
            self.enabled = False
            self.viewport.toolbar.set_beam_physical(False)
            self.viewport.plotter.render()
        self.sync_availability()

    def set_enabled(self, enabled: bool) -> None:
        """Toggle physical beams in either editor or stored-result context."""
        requested = bool(enabled)
        if self.viewport.stage == "RESULTS":
            self._set_result_enabled(requested)
        else:
            self._set_editor_enabled(requested)

    def prepare_options(self, result, field, options=None) -> dict:
        """Inject expanded current/next grids into the existing result pipeline."""
        prepared = dict(options or {})
        self._last_options = dict(options or {})
        if not self.enabled or result is None or self.viewport.stage != "RESULTS":
            return prepared

        try:
            representation = self._ensure_representation(
                result,
                field,
                show_progress=False,
            )
            animation = dict(prepared.get("_animation", {}) or {})
            source = animation.get("source_grid")
            if source is None:
                source = self._grid(result, field)
            animation["source_grid"] = self._expand(
                representation,
                source,
                result,
                field,
            )

            next_field = animation.get("next_field")
            if next_field is not None:
                next_grid = animation.get("next_grid")
                if next_grid is None:
                    next_grid = self._grid(result, next_field)
                animation["next_grid"] = self._expand(
                    representation,
                    next_grid,
                    result,
                    next_field,
                )
            prepared["_animation"] = animation
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            self._reject(str(exc))
        return prepared

    def reset(self) -> None:
        """Disable the display toggle while retaining reusable result caches."""
        self._clear_editor_display(render=False)
        self.enabled = False
        self._last_options = {}
        self.viewport.toolbar.set_beam_physical(False)
        self.viewport.toolbar.set_beam_available(False)

    def _set_result_enabled(self, requested: bool) -> None:
        result = getattr(self.viewport, "_active_result", None)
        field = getattr(self.viewport, "_active_result_field", None)
        if requested and result is None:
            self._reject("Open a solver result before enabling physical beams")
            return
        if requested:
            try:
                # Result topology is intentionally cached. The progress dialog
                # appears only on the first build; later toggles reuse it.
                self._ensure_representation(result, field, show_progress=True)
            except (OSError, RuntimeError, TypeError, ValueError) as exc:
                self._reject(str(exc))
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
            # Editor geometry is deliberately rebuilt on every activation so it
            # always reflects the live mesh, section assignment, profile and n1.
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
            raise ValueError("The current model has no beam elements with assigned profiles")

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
                beam_ids = tuple(int(item.source_element_id) for item in owned)
                cell_ids = np.asarray(expanded.cell_data["element_id"], dtype=np.int64)
                indices = np.flatnonzero(np.isin(cell_ids, beam_ids))
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
            raise ValueError(f"Generate a mesh for Part '{part.name}' before showing beams")
        grid = build_grid(
            snapshot,
            instance,
            include_all_dimensions=True,
        )
        if grid is None:
            raise ValueError(f"Part '{part.name}' has no renderable finite elements")
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
        """Rebuild the active result once after a representation toggle."""
        result = getattr(self.viewport, "_active_result", None)
        if result is None:
            return
        options = dict(self._last_options)
        # The animation fast path assumes invariant topology. Switching between
        # line beams and expanded beam surfaces changes topology, so force one
        # ordinary rebuild. The Time Manager can resume in-place animation on
        # its next frame with the newly established representation.
        options.pop("_animation", None)
        self.viewport.scene.show_result(
            result,
            getattr(self.viewport, "_active_result_field", None),
            options,
        )

    def _ensure_representation(self, result, field, *, show_progress: bool):
        project = self._project()
        if project is None:
            raise ValueError("Physical beam rendering requires an active project")
        source = str(getattr(result, "source_file", "") or "")
        identity = str(getattr(result, "id", "") or source or id(result))
        key = (identity, source, id(project))
        cached = self._representations.get(key)
        if cached is not None:
            return cached

        grid = self._grid(result, field)
        dialog = self._progress_dialog() if show_progress else None

        def progress(current, total, label):
            if dialog is None:
                return
            dialog.setRange(0, max(1, int(total)))
            dialog.setValue(int(current))
            dialog.setLabelText(str(label))
            QApplication.processEvents()

        try:
            representation = build_beam_physical_representation(
                project,
                grid,
                progress,
            )
            if dialog is not None:
                dialog.setValue(dialog.maximum())
                QApplication.processEvents()
        finally:
            if dialog is not None:
                dialog.close()

        self._representations[key] = representation
        return representation

    def _expand(self, representation, grid, result, field):
        if "_opencae_beam_xi" in grid.point_data:
            return grid
        step_id = _metadata_int(field, "step_id")
        forces = self._forces(result, step_id)
        return representation.expand(
            grid,
            _scalar_name(field),
            element_nodal_forces=forces,
        )

    def _forces(self, result, step_id):
        source = str(getattr(result, "source_file", "") or "")
        key = (source, step_id)
        if key not in self._section_forces:
            self._section_forces[key] = load_local_section_forces(source, step_id)
        return self._section_forces[key]

    def _grid(self, result, field):
        source = str(getattr(result, "source_file", "") or "")
        if not source:
            raise ValueError("The selected result has no solver result file")
        return self._loader.pyvista_grid(
            source,
            _metadata_int(field, "step_id"),
            _metadata_int(field, "frame_id"),
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
        self.viewport.message.emit(message or "Could not generate physical beams")
        self.viewport.plotter.render()

    def _project(self):
        if self.viewport.stage == "RESULTS":
            result = getattr(self.viewport, "_active_result", None)
            source = str(getattr(result, "source_file", "") or "")
            if source.lower().endswith(".res"):
                try:
                    project = self._loader.model_project(source)
                except (OSError, RuntimeError, TypeError, ValueError):
                    return None
                if project is not None:
                    return project
        return self.viewport.store.project if self.viewport.store is not None else None

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

    def _project_has_beams(self, project) -> bool:
        return bool(beam_occurrences(project))

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
    """Return the one beam-display controller owned by a viewport."""
    controller = getattr(viewport, "_beam_physical_controller", None)
    if controller is None:
        controller = BeamPhysicalDisplayController(viewport)
        viewport._beam_physical_controller = controller
    controller.bind_toolbar()
    return controller


def _metadata_int(field, key: str) -> int | None:
    metadata = getattr(field, "metadata", {}) or {}
    value = metadata.get(key)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _scalar_name(field) -> str | None:
    if field is None:
        return None
    metadata = getattr(field, "metadata", {}) or {}
    block = str(metadata.get("block", getattr(field, "name", "")) or "")
    component = str(metadata.get("component", "Magnitude") or "Magnitude")
    return f"{block}:{component}" if block else None
