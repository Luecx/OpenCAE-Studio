from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QMessageBox, QVBoxLayout

from .element_control_order import ElementOrderPanel
from .element_control_preview import ElementControlPreview
from .element_control_target import ElementControlTarget
from .element_control_topologies import ElementTopologyTable


class ElementControlDialog(QDialog):
    committed = pyqtSignal(object); preview_changed = pyqtSignal(object)

    def __init__(self, analyze, preview, selection_provider, element_sets=(), control=None, initial=(), parent=None):
        super().__init__(parent); self.analyze = analyze; self.preview_provider = preview; self.current_preview = None
        self.setWindowTitle("Element Controls"); self.setModal(False); self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True); self.setMinimumWidth(660)
        root = QVBoxLayout(self); root.setContentsMargins(18, 16, 18, 14); root.setSpacing(10)
        title = QLabel("Element Controls"); title.setObjectName("PanelTitle"); root.addWidget(title)
        targets = control.targets if control else initial; self.target = ElementControlTarget(selection_provider, element_sets, targets); root.addWidget(self.target)
        root.addWidget(QLabel("Topologies in Target")); self.topologies = ElementTopologyTable(); root.addWidget(self.topologies)
        root.addWidget(QLabel("Interpolation Order and Formulation")); self.order = ElementOrderPanel(); root.addWidget(self.order)
        root.addWidget(QLabel("Propagation Preview")); self.preview = ElementControlPreview(); root.addWidget(self.preview)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Apply).setObjectName("PrimaryButton"); buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._apply)
        buttons.rejected.connect(self.close); root.addWidget(buttons)
        self.target.changed.connect(self.refresh); self.topologies.topology_changed.connect(self._topology_changed); self.order.changed.connect(self._update_preview); self.refresh()
        if control:
            self.topologies.select_key(control.topology); self.order.choose(control.order); self.order.set_formulation(control.formulation)

    def mode(self): return self.target.mode()
    def update_selection(self): self.target.capture()

    def refresh(self):
        preferred = self.topologies.summary().key if self.topologies.summary() else None
        self.topologies.set_summaries(self.analyze(self.target.targets()), preferred)
        if self.topologies.summary() is None: self._topology_changed(None)

    def _topology_changed(self, summary): self.order.set_summary(summary); self._update_preview()

    def _update_preview(self):
        summary = self.topologies.summary(); self.current_preview = self.preview_provider(self.target.targets(), summary.key) if summary else None
        self.preview.set_preview(self.current_preview, self.order.order()); self.preview_changed.emit(self.current_preview)

    def _apply(self):
        summary, order = self.topologies.summary(), self.order.order()
        if not summary or not order: QMessageBox.warning(self, "Element Controls", "Select a topology and a definite interpolation order."); return
        if self.current_preview and self.current_preview.additional:
            text = f"{self.current_preview.additional:,} neighboring elements outside the direct selection must also be converted. Continue?"
            if QMessageBox.question(self, "Propagate element order", text) != QMessageBox.StandardButton.Yes: return
        self.committed.emit({"targets":self.target.targets(), "topology":summary.key, "order":order, "formulation":self.order.formulation.currentText()})
