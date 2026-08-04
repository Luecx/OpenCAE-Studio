from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class FallbackViewport(QWidget):
    selection_changed = pyqtSignal(object)
    message = pyqtSignal(str)
    section_changed = pyqtSignal(object)

    def __init__(self, store=None, parent=None):
        super().__init__(parent)
        self.display_mode = "geometry"
        self.visibility = None
        layout = QVBoxLayout(self)
        label = QLabel("3D viewport unavailable\nInstall pyvista, pyvistaqt and VTK")
        label.setObjectName("MutedLabel")
        label.setAlignment(__import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

    def refresh(self, *_): pass
    def request_refresh(self, *_, **__): pass
    def fit_view(self): pass
    def toggle_mesh(self): self.set_display_mode("mesh" if self.display_mode == "geometry" else "geometry")
    def set_display_mode(self, mode): self.display_mode = str(mode or "geometry")
    def clear_scene(self): pass
    def set_stage(self, *_): pass
    def show_model_selection(self, *_): pass
    def show_solution(self, *_): pass
    def close_solution(self, *_): pass
    def is_showing_result(self, *_): return False
    def begin_context_pick(self, *_): pass
    def begin_datum_reference_pick(self, *_): pass
    def begin_selection_session(self, *_, **__): pass
    def cancel_context_pick(self): pass
    def show_datum_preview(self, *_): pass
    def hide_datum_preview(self): pass
    def show_datum_reference_preview(self, *_): pass
    def clear_datum_reference_preview(self): pass
    def show_reference_point_preview(self, *_): pass
    def clear_reference_point_preview(self): pass
    def show_region_preview(self, *_, **__): pass
    def clear_region_preview(self, *_): pass
    def clear_region_previews(self, *_): pass
    def suspend_model_selection_preview(self): pass
    def restore_model_selection_preview(self): pass
