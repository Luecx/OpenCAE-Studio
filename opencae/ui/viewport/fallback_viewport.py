from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class FallbackViewport(QWidget):
    selection_changed = pyqtSignal(object); message = pyqtSignal(str)
    def __init__(self, store=None, parent=None):
        super().__init__(parent); layout = QVBoxLayout(self)
        label = QLabel("3D viewport unavailable\nInstall pyvista, pyvistaqt and VTK"); label.setObjectName("MutedLabel")
        label.setAlignment(__import__("PyQt6.QtCore",fromlist=["Qt"]).Qt.AlignmentFlag.AlignCenter); layout.addWidget(label)
    def refresh(self,*_): pass
    def request_refresh(self,*_,**__): pass
    def fit_view(self): pass
    def toggle_mesh(self): pass
    def clear_scene(self): pass
    def set_stage(self,*_): pass
    def show_model_selection(self,*_): pass
    def show_solution(self,*_): pass
    def begin_context_pick(self,*_): pass
    def begin_datum_reference_pick(self,*_): pass
    def begin_selection_session(self,*_,**__): pass
    def cancel_context_pick(self): pass
    def show_datum_preview(self,*_): pass
    def hide_datum_preview(self): pass
    def show_region_preview(self,*_,**__): pass
    def clear_region_preview(self,*_): pass
    def clear_region_previews(self,*_): pass
    def suspend_model_selection_preview(self): pass
    def restore_model_selection_preview(self): pass
