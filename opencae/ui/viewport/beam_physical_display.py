"""Own lazy physical-beam generation and result-grid expansion for the viewport."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QProgressDialog

from opencae.results import FrdLoader
from opencae.results.beam_physical_representation import (
    build_beam_physical_representation,
)
from opencae.results.femaster_res_section_forces import (
    load_local_section_forces,
)


class BeamPhysicalDisplayController:
    """Cache beam topology once and project every displayed result frame onto it."""

    def __init__(self, viewport) -> None:
        self.viewport = viewport
        self.enabled = False
        self._bound = False
        self._loader = FrdLoader()
        self._representations = {}
        self._section_forces = {}
        self._last_options: dict = {}

    def bind_toolbar(self) -> None:
        """Connect the viewport Beam toggle exactly once."""
        if self._bound:
            return
        self.viewport.toolbar.beam_physical_changed.connect(self.set_enabled)
        self._bound = True

    def result_changed(self, result) -> None:
        """Update toolbar availability when the active stored result changes."""
        available = bool(result is not None and getattr(result, "source_file", ""))
        self.viewport.toolbar.set_beam_available(available)

    def set_enabled(self, enabled: bool) -> None:
        """Toggle beam surfaces, building the current result lazily on first use."""
        requested = bool(enabled)
        result = getattr(self.viewport, "_active_result", None)
        field = getattr(self.viewport, "_active_result_field", None)
        if requested and result is None:
            self._reject("Open a solver result before enabling physical beams")
            return
        if requested:
            try:
                self._ensure_representation(result, field, show_progress=True)
            except (OSError, RuntimeError, TypeError, ValueError) as exc:
                self._reject(str(exc))
                return
        self.enabled = requested
        self.viewport.toolbar.set_beam_physical(requested)
        self._rerender_active()

    def prepare_options(self, result, field, options=None) -> dict:
        """Inject expanded current/next grids into the existing result pipeline."""
        prepared = dict(options or {})
        self._last_options = dict(options or {})
        if not self.enabled or result is None:
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
        """Disable the display toggle while retaining reusable runtime caches."""
        self.enabled = False
        self._last_options = {}
        self.viewport.toolbar.set_beam_physical(False)
        self.viewport.toolbar.set_beam_available(False)

    def _rerender_active(self) -> None:
        """Rebuild only the active result presentation after a toggle change."""
        result = getattr(self.viewport, "_active_result", None)
        if result is None:
            return
        self.viewport.scene.show_result(
            result,
            getattr(self.viewport, "_active_result_field", None),
            dict(self._last_options),
        )

    def _ensure_representation(self, result, field, *, show_progress: bool):
        project = self.viewport.store.project if self.viewport.store is not None else None
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

    def _progress_dialog(self) -> QProgressDialog:
        dialog = QProgressDialog(
            "Generating beam profiles…",
            "",
            0,
            0,
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
        self.enabled = False
        self.viewport.toolbar.set_beam_physical(False)
        self.viewport.message.emit(message or "Could not generate physical beams")


def beam_physical_controller(viewport) -> BeamPhysicalDisplayController:
    """Return the one lazy beam-display controller owned by a viewport."""
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
