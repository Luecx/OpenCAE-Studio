from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from opencae.geometry import GeometryService
from opencae.ui.core.theme import PALETTE
from .context_pick import ContextPickManager
from .datum_preview import DatumPreview
from .element_control_overlay import ElementControlOverlay
from .model_selection_display import highlight_members, show_model_selection, show_pending_members
from .pyvista_picker import PyVistaPicker
from .pyvista_scene import PyVistaScene
from .result_query_state import ResultQueryState
from .seed_label_events import handle_seed_label_event
from .safe_qt_interactor import SafeQtInteractor
from .selection_toolbar import SelectionToolbar
from .viewport_canvas import ViewportCanvas


class PyVistaViewport(QWidget):
    selection_changed = pyqtSignal(object); seed_adjust_requested = pyqtSignal(str,int); message = pyqtSignal(str)
    def __init__(self, store=None, parent=None):
        super().__init__(parent); self.store = store; self.service = GeometryService(); self.stage = "PART"
        self.selection_mode = "none"; self.display_mode = "geometry"; self._field_id = None
        self._refresh_pending = self._fit_pending = False; self._active_result = self._active_result_field = self._pending_members = None
        self._pending_element_control_preview = None
        self._region_previews = {}
        layout = QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        self.toolbar = SelectionToolbar(); layout.addWidget(self.toolbar); self.canvas = ViewportCanvas(); layout.addWidget(self.canvas,1)
        self.plotter = SafeQtInteractor(self.canvas); self.canvas.set_render_widget(self.plotter); self.plotter.set_background(PALETTE["viewport"])
        self.view_cube = self.canvas.cube; self.query_panel = self.canvas.query; self.result_selection_panel = self.canvas.result_selection; self.view_cube.view_requested.connect(self._set_view)
        self.context_pick = ContextPickManager(self); self.datum_preview = DatumPreview(); self.element_control_overlay = ElementControlOverlay(); self.result_query = ResultQueryState(self)
        self.picker = PyVistaPicker(self); self.scene = PyVistaScene(self); self.picker.enable()
        for watched in (self.plotter, getattr(self.plotter,"interactor",None)):
            if watched is not None: watched.installEventFilter(self)
        self.toolbar.mode_changed.connect(self.set_selection_mode); self.toolbar.display_changed.connect(self.set_display_mode); self.toolbar.fit_requested.connect(self.fit_view)
    def request_refresh(self, *_args, fit=False):
        self._fit_pending = self._fit_pending or bool(fit)
        if not self._refresh_pending: self._refresh_pending = True; QTimer.singleShot(0,self._perform_refresh)
    def refresh(self, *_args): self.request_refresh()
    def _perform_refresh(self):
        self._refresh_pending = False; fit = self._fit_pending; self._fit_pending = False
        self.scene.refresh(self.store.active_part() if self.store else None,fit=fit)
        self._restore_region_previews(render=True)
        if self._pending_members is not None:
            members = self._pending_members; self._pending_members = None; self.picker.show_labels(members,render=False); self.scene.region_overlay.show(self.plotter,self.scene,members); self.plotter.render()
        if self._pending_element_control_preview is not None:
            selected, propagated = self._pending_element_control_preview
            self.element_control_overlay.show(self.plotter, self.scene, selected, propagated); self.plotter.render()
    def set_selection_mode(self, mode):
        mode = str(mode or "none").lower()
        if mode != "none" and not self.context_pick.active:
            mode = "none"
        self.selection_mode = mode
        self.toolbar.set_mode(mode)
        # Changing a dialog-owned pick mode must not clear the object selected
        # in the project tree. Only temporary viewport pick state is reset.
        self.picker.clear(False)
        self.picker.configure()
        if mode != "none":
            self.message.emit(f"Selection mode: {mode.title()}")
    def set_display_mode(self, mode):
        if mode != self.display_mode:
            self.display_mode = mode
            self.toolbar.set_display(mode)
            self.context_pick.refresh_for_display()
            self.request_refresh()
    def set_stage(self, stage):
        self.toolbar.setVisible(True); self.toolbar.set_results_mode(stage == "RESULTS")
        if stage == self.stage: return
        previous = self.stage; self.stage = stage; self.picker.clear(False, False); self.picker.configure()
        if stage != "RESULTS": self.result_query.configure(""); self.result_selection_panel.clear_selection()
        elif self._active_result is not None: self.result_selection_panel.show()
        if self.scene.same_display_context(previous,stage): self.scene.update_stage_overlays(stage)
        else: self.request_refresh()
    def handle_entities(self, entities): return self.context_pick.consume(entities)
    def begin_context_pick(self, allowed, callback): self.context_pick.begin(allowed,callback)
    def begin_selection_session(self, policy, callback, finished=None): self.context_pick.begin(policy, callback, finished=finished)
    def cancel_context_pick(self): self.context_pick.cancel()
    def show_datum_preview(self, values): self.datum_preview.show(self.plotter,self.scene,values)
    def hide_datum_preview(self): self.datum_preview.clear(self.plotter); self.plotter.render()
    def fit_view(self): self.scene.fit()
    def _set_view(self, name):
        {"TOP":self.plotter.view_xy,"FRONT":self.plotter.view_xz,"RIGHT":self.plotter.view_yz}.get(name,self.plotter.view_isometric)(); self.plotter.reset_camera(); self.plotter.render()
    def toggle_mesh(self): self.set_display_mode("mesh" if self.display_mode == "geometry" else "geometry")
    def clear_scene(self):
        self._region_previews.clear(); self.scene.clear()
    def clear_selection(self): self.picker.clear()
    def show_region_preview(self, channel, definition, **style):
        self._region_previews[str(channel)] = (definition, dict(style))
        if self._refresh_pending:
            return
        self.scene.selection_preview_overlay.show_channel(
            self.plotter, self.scene, str(channel), definition, **style
        )
        self.plotter.render()
    def clear_region_preview(self, channel):
        self._region_previews.pop(str(channel), None)
        self.scene.selection_preview_overlay.clear_channel(self.plotter, str(channel))
        self.plotter.render()
    def clear_region_previews(self, prefix=None):
        channels = tuple(self._region_previews)
        if prefix is not None:
            channels = tuple(value for value in channels if value.startswith(str(prefix)))
        for channel in channels:
            self._region_previews.pop(channel, None)
            self.scene.selection_preview_overlay.clear_channel(self.plotter, channel)
        self.plotter.render()
    def _restore_region_previews(self, render=True):
        for channel, (definition, style) in self._region_previews.items():
            self.scene.selection_preview_overlay.show_channel(
                self.plotter, self.scene, channel, definition, **style
            )
        if render:
            self.plotter.render()
    def show_element_control_preview(self, selected, propagated):
        self._pending_element_control_preview = (tuple(selected), tuple(propagated))
        if self._refresh_pending: return
        self.element_control_overlay.show(self.plotter, self.scene, selected, propagated); self.plotter.render()
    def hide_element_control_preview(self):
        self._pending_element_control_preview = None
        self.element_control_overlay.clear(self.plotter); self.plotter.render()
    def show_seed_preview(self,seeds): self.scene.show_seed_preview(seeds)
    def hide_seed_preview(self): self.scene.hide_seed_preview()
    def show_model_selection(self,entity): show_model_selection(self,entity)
    def _show_pending_members(self): show_pending_members(self)
    def highlight_members(self,members): highlight_members(self,members)
    def show_solution(self,result,field=None,options=None):
        self._active_result=result; self._active_result_field=field; self.result_selection_panel.set_selection((options or {}).get("selection", {}))
        self.canvas._position_overlays(); self.scene.show_result(result,field,options)
    def close_solution(self):
        self._active_result=self._active_result_field=None; self.result_query.configure(""); self.result_selection_panel.clear_selection(); self.request_refresh(fit=True)
    def eventFilter(self,watched,event): return True if handle_seed_label_event(self,watched,event) else super().eventFilter(watched,event)
