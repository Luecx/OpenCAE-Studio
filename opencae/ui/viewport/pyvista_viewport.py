"""Qt/PyVista viewport coordinating scene refreshes, picking, and previews."""

from __future__ import annotations

from PyQt6.QtCore import QEvent, QTimer, pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from opencae.geometry import GeometryService
from opencae.ui.core.theme import PALETTE
from .click_gesture import ClickGestureTracker
from .context_pick import ContextPickManager
from .datum_preview import DatumPreview
from .datum_reference import reference_from_hit
from .datum_reference_overlay import DatumReferenceOverlay
from .element_control_overlay import ElementControlOverlay
from .model_selection_display import (
    highlight_members,
    show_model_selection,
    show_pending_members,
)
from .pyvista_picker import PyVistaPicker
from .pyvista_scene import PyVistaScene
from .result_query_state import ResultQueryState
from .safe_qt_interactor import SafeQtInteractor
from .scene_camera import camera_position, restore_camera
from .section_view import SectionViewController
from .seed_label_events import handle_seed_label_event
from .selection_toolbar import SelectionToolbar
from .viewport_canvas import ViewportCanvas


class PyVistaViewport(QWidget):
    """Own the interactive viewport surface and coordinate its UI-facing state."""

    selection_changed = pyqtSignal(object)
    seed_adjust_requested = pyqtSignal(str, int)
    message = pyqtSignal(str)
    section_changed = pyqtSignal(object)

    def __init__(self, store=None, parent=None):
        """Build the render widget, scene services, overlays, and gesture routing."""
        super().__init__(parent)
        self.store = store
        self.service = GeometryService()
        self.stage = "PART"
        self.selection_mode = "none"
        self.display_mode = "geometry"
        self._field_id = None
        self._refresh_pending = False
        self._fit_pending = False
        self._active_result = None
        self._active_result_field = None
        self._pending_members = None
        self._pending_element_control_preview = None
        self._region_previews = {}
        self._reference_point_preview = None
        self._datum_reference_preview = ()
        self._click_gesture = ClickGestureTracker()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.toolbar = SelectionToolbar()
        layout.addWidget(self.toolbar)
        self.canvas = ViewportCanvas()
        layout.addWidget(self.canvas, 1)
        self.plotter = SafeQtInteractor(self.canvas)
        self.canvas.set_render_widget(self.plotter)
        self.plotter.set_background(PALETTE["viewport"])
        self.view_cube = self.canvas.cube
        self.query_panel = self.canvas.query
        self.result_selection_panel = self.canvas.result_selection
        self.view_cube.view_requested.connect(self._set_view)

        self.context_pick = ContextPickManager(self)
        self.datum_preview = DatumPreview()
        self.datum_reference_overlay = DatumReferenceOverlay()
        self.element_control_overlay = ElementControlOverlay()
        self.result_query = ResultQueryState(self)
        self.section_view = SectionViewController(self)
        self.picker = PyVistaPicker(self)
        self.scene = PyVistaScene(self)
        self.picker.enable()

        for watched in (self.plotter, getattr(self.plotter, "interactor", None)):
            if watched is not None:
                watched.installEventFilter(self)
        self.toolbar.mode_changed.connect(self.set_selection_mode)
        self.toolbar.display_changed.connect(self.set_display_mode)
        self.toolbar.fit_requested.connect(self.fit_view)

    def request_refresh(self, *_args, fit=False):
        """Coalesce full-scene refresh requests onto the next Qt event turn."""
        self._fit_pending = self._fit_pending or bool(fit)
        if not self._refresh_pending:
            self._refresh_pending = True
            QTimer.singleShot(0, self._perform_refresh)

    def refresh(self, *_args):
        """Compatibility alias for callers requesting a full scene refresh."""
        self.request_refresh()

    def _perform_refresh(self):
        """Rebuild once, restore all pending overlays, then render one frame."""
        self._refresh_pending = False
        fit = self._fit_pending
        self._fit_pending = False
        self.scene.refresh(
            self.store.active_part() if self.store else None,
            fit=fit,
        )
        self._restore_region_previews(render=False)
        self._restore_reference_point_preview(render=False)
        self._restore_datum_reference_preview(render=False)

        if self._pending_members is not None:
            members = self._pending_members
            self._pending_members = None
            self.picker.show_labels(members, render=False)
            self.scene.region_overlay.show(self.plotter, self.scene, members)
        if self._pending_element_control_preview is not None:
            selected, propagated = self._pending_element_control_preview
            self.element_control_overlay.show(
                self.plotter,
                self.scene,
                selected,
                propagated,
            )
        self.plotter.render()

    def apply_topology_visibility(self, owner_id, kind):
        """Apply scoped topology visibility without rebuilding CAD when possible."""
        if self._refresh_pending:
            # The queued rebuild will consume the latest VisibilityState.
            return
        if not self.scene.apply_topology_visibility(owner_id, kind):
            self.request_refresh()

    def set_selection_mode(self, mode):
        """Switch the active context-picking mode and synchronize actor styles."""
        mode = str(mode or "none").lower()
        if mode != "none" and not self.context_pick.active:
            mode = "none"
        self.selection_mode = mode
        self.toolbar.set_mode(mode)
        self.picker.clear(False, False)
        self.picker.configure()
        # Picker configuration may restore normal point visibility or line
        # widths. Reapply dialog-owned datum highlights afterwards so completed
        # Point 1 / Edge / Face selections stay visible while the next field is
        # being picked.
        self.datum_reference_overlay.reapply()
        self.plotter.render()
        if mode != "none":
            self.message.emit(f"Selection mode: {mode.title()}")

    def set_display_mode(self, mode):
        """Switch between Geometry and Mesh base-scene presentation."""
        if mode != self.display_mode:
            self.display_mode = mode
            self.toolbar.set_display(mode)
            self.context_pick.refresh_for_display()
            self._sync_meshability_legend()
            self.request_refresh()

    def set_stage(self, stage):
        """Switch workflow stage while preserving a compatible base scene."""
        self.toolbar.setVisible(True)
        self.toolbar.set_results_mode(stage == "RESULTS")
        if stage == self.stage:
            return
        previous = self.stage
        self.stage = stage
        self._click_gesture.reset()
        self.picker.clear(False, False)
        self.picker.configure()
        self.datum_reference_overlay.reapply()
        self._sync_meshability_legend()
        if stage != "RESULTS":
            self.section_view.clear_scene()
            self.result_query.configure("")
            self.result_selection_panel.clear_selection()
        elif self._active_result is not None:
            self.result_selection_panel.show()
        if self.scene.same_display_context(previous, stage):
            self.scene.update_stage_overlays(stage)
        else:
            self.request_refresh()

    def _sync_meshability_legend(self):
        visible = (
            self.stage == "PART"
            and self.display_mode == "geometry"
            and self.scene.snapshot is not None
        )
        self.canvas.meshability.setVisible(visible)
        self.canvas._position_overlays()

    def handle_entities(self, entities):
        return self.context_pick.consume(entities)

    def begin_context_pick(self, allowed, callback):
        self.context_pick.begin(allowed, callback)

    def begin_datum_reference_pick(self, allowed, callback, finished=None):
        def selected(hit):
            try:
                callback(reference_from_hit(self, hit))
            except (TypeError, ValueError) as exc:
                self.message.emit(str(exc))

        self.context_pick.begin(allowed, selected, finished=finished)
        self.datum_reference_overlay.reapply()
        self.plotter.render()

    def begin_selection_session(self, policy, callback, finished=None):
        self.context_pick.begin(policy, callback, finished=finished)

    def cancel_context_pick(self):
        self._click_gesture.reset()
        self.context_pick.cancel()

    def show_datum_preview(self, values):
        self.datum_preview.show(self.plotter, self.scene, values)

    def hide_datum_preview(self):
        self.datum_preview.clear(self.plotter)
        self.plotter.render()

    def show_datum_reference_preview(self, references):
        self._datum_reference_preview = tuple(
            dict(reference)
            for reference in tuple(references or ())
            if reference
        )
        if self._refresh_pending:
            return
        self._restore_datum_reference_preview(render=True)

    def clear_datum_reference_preview(self):
        if not self._datum_reference_preview:
            return
        self._datum_reference_preview = ()
        self.datum_reference_overlay.clear(self.plotter)
        self.plotter.render()

    def _restore_datum_reference_preview(self, render=True):
        camera = camera_position(self.plotter)
        self.datum_reference_overlay.show(
            self.plotter,
            self.scene,
            self._datum_reference_preview,
        )
        restore_camera(self.plotter, camera)
        if render:
            self.plotter.render()

    def show_reference_point_preview(self, name, position):
        self._reference_point_preview = (
            str(name),
            tuple(float(value) for value in position),
        )
        self._restore_reference_point_preview(render=True)

    def clear_reference_point_preview(self):
        if self._reference_point_preview is None:
            return
        self._reference_point_preview = None
        self.scene.reference_overlay.clear_preview(self.plotter)
        self.plotter.render()

    def _restore_reference_point_preview(self, render=True):
        if self._reference_point_preview is None:
            return
        name, position = self._reference_point_preview
        self.scene.reference_overlay.show_preview(
            self.plotter,
            name,
            position,
        )
        if render:
            self.plotter.render()

    def fit_view(self):
        self.scene.fit()

    def _set_view(self, name):
        {
            "TOP": self.plotter.view_xy,
            "FRONT": self.plotter.view_xz,
            "RIGHT": self.plotter.view_yz,
        }.get(name, self.plotter.view_isometric)()
        self.plotter.reset_camera()
        self.plotter.render()

    def toggle_mesh(self):
        self.set_display_mode(
            "mesh" if self.display_mode == "geometry" else "geometry"
        )

    def clear_scene(self):
        self._region_previews.clear()
        self._reference_point_preview = None
        self._datum_reference_preview = ()
        self._click_gesture.reset()
        self.datum_reference_overlay.clear(self.plotter)
        self.scene.clear()

    def clear_selection(self):
        self.picker.clear()

    def show_region_preview(self, channel, definition, **style):
        self._region_previews[str(channel)] = (definition, dict(style))
        if self._refresh_pending:
            return
        camera = camera_position(self.plotter)
        self.scene.selection_preview_overlay.show_channel(
            self.plotter,
            self.scene,
            str(channel),
            definition,
            **style,
        )
        restore_camera(self.plotter, camera)
        self.plotter.render()

    def clear_region_preview(self, channel):
        channel = str(channel)
        if channel not in self._region_previews:
            return
        camera = camera_position(self.plotter)
        self._region_previews.pop(channel, None)
        self.scene.selection_preview_overlay.clear_channel(
            self.plotter,
            channel,
        )
        restore_camera(self.plotter, camera)
        self.plotter.render()

    def clear_region_previews(self, prefix=None):
        channels = tuple(self._region_previews)
        if prefix is not None:
            channels = tuple(
                value
                for value in channels
                if value.startswith(str(prefix))
            )
        if not channels:
            return
        camera = camera_position(self.plotter)
        for channel in channels:
            self._region_previews.pop(channel, None)
            self.scene.selection_preview_overlay.clear_channel(
                self.plotter,
                channel,
            )
        restore_camera(self.plotter, camera)
        self.plotter.render()

    def suspend_model_selection_preview(self):
        """Temporarily hide tree-owned selection while a dialog edits it."""
        camera = camera_position(self.plotter)
        for channel in tuple(self._region_previews):
            if channel.startswith("model-selection"):
                self._region_previews.pop(channel, None)
                self.scene.selection_preview_overlay.clear_channel(
                    self.plotter,
                    channel,
                )
        self.scene.region_overlay.clear(self.plotter)
        self.picker.clear(False, False)
        self.datum_reference_overlay.reapply()
        restore_camera(self.plotter, camera)
        self.plotter.render()

    def restore_model_selection_preview(self):
        entity = self.store.selection if self.store is not None else None
        self.show_model_selection(entity)

    def _restore_region_previews(self, render=True):
        camera = camera_position(self.plotter)
        for channel, (definition, style) in self._region_previews.items():
            self.scene.selection_preview_overlay.show_channel(
                self.plotter,
                self.scene,
                channel,
                definition,
                **style,
            )
        restore_camera(self.plotter, camera)
        if render:
            self.plotter.render()

    def show_element_control_preview(self, selected, propagated):
        self._pending_element_control_preview = (
            tuple(selected),
            tuple(propagated),
        )
        if self._refresh_pending:
            return
        self.element_control_overlay.show(
            self.plotter,
            self.scene,
            selected,
            propagated,
        )
        self.plotter.render()

    def hide_element_control_preview(self):
        if self._pending_element_control_preview is None:
            return
        self._pending_element_control_preview = None
        self.element_control_overlay.clear(self.plotter)
        self.plotter.render()

    def show_seed_preview(self, seeds):
        self.scene.show_seed_preview(seeds)

    def hide_seed_preview(self):
        self.scene.hide_seed_preview()

    def show_model_selection(self, entity):
        show_model_selection(self, entity)

    def _show_pending_members(self):
        show_pending_members(self)

    def highlight_members(self, members):
        highlight_members(self, members)

    def show_solution(self, result, field=None, options=None):
        self._active_result = result
        self._active_result_field = field
        self.result_selection_panel.set_selection(
            (options or {}).get("selection", {})
        )
        self.canvas._position_overlays()
        self.scene.show_result(result, field, options)

    def is_showing_result(self, result):
        return bool(
            self._active_result is not None
            and result is not None
            and getattr(self._active_result, "id", None)
            == getattr(result, "id", None)
        )

    def close_solution(self, result=None):
        if result is not None and not self.is_showing_result(result):
            return
        self.section_view.clear_scene()
        self._active_result = None
        self._active_result_field = None
        self.result_query.configure("")
        self.result_selection_panel.clear_selection()
        self.request_refresh(fit=True)

    def _event_display_position(self, watched, event):
        try:
            position = event.position()
            widget_width = max(1.0, float(watched.width()))
            widget_height = max(1.0, float(watched.height()))
            render_window = self.plotter.GetRenderWindow()
            render_width, render_height = render_window.GetSize()
            render_width = max(1.0, float(render_width))
            render_height = max(1.0, float(render_height))
        except (AttributeError, TypeError, ValueError, RuntimeError):
            return None

        # Qt uses a top-left origin and logical pixels. VTK uses a bottom-left
        # origin and may render in device pixels. Scaling through the actual
        # render-window size handles both HiDPI and ordinary displays.
        x = float(position.x()) * render_width / widget_width
        y = (
            widget_height - 1.0 - float(position.y())
        ) * render_height / widget_height
        if x < 0.0 or y < 0.0 or x >= render_width or y >= render_height:
            return None
        return x, y

    def _handle_click_event(self, watched, event):
        """Dispatch only stationary left-click releases to viewport pickers."""
        try:
            event_type = event.type()
        except (AttributeError, RuntimeError):
            return

        if event_type == QEvent.Type.MouseButtonPress:
            self._click_gesture.press(event)
            return
        if event_type == QEvent.Type.MouseMove:
            self._click_gesture.move(event)
            return
        if event_type != QEvent.Type.MouseButtonRelease:
            return
        if not self._click_gesture.release_is_click(event):
            return

        cursor = self._event_display_position(watched, event)
        if cursor is None:
            return
        if self.result_query.handles_direct_click():
            self.result_query.pick_display_position(cursor)
            return
        if self.picker.handles_direct_click():
            self.picker.pick_display_position(cursor)

    def eventFilter(self, watched, event):
        """Route seed-label and drag-safe click gestures without blocking VTK."""
        if handle_seed_label_event(self, watched, event):
            return True
        self._handle_click_event(watched, event)
        return super().eventFilter(watched, event)
