from pathlib import Path
from shutil import copy2

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QButtonGroup, QHBoxLayout, QMessageBox, QToolButton, QWidget

from opencae.results import FrdLoader
from opencae.ui.actions.ids import A
from opencae.ui.core.icon_factory import IconKind, make_icon
from opencae.ui.viewport.result_visualization import auto_deformation_scale
from .result_deformation import ResultDeformationButton
from .result_field_menu import ResultFieldButton
from .result_range import ResultRangeButton
from .result_section import ResultSectionButton
from .result_group import ResultRibbonGroup
from .result_widgets import action_button, ribbon_button


class ResultsPage(QWidget):
    result_requested = pyqtSignal(object, object, dict)
    def __init__(self, actions=None, parent=None):
        super().__init__(parent); self.actions = actions; self.result = None; self.loader = FrdLoader(); self._build()

    def _build(self):
        layout = QHBoxLayout(self); layout.setContentsMargins(5, 0, 0, 0); layout.setSpacing(0)
        open_button = action_button(self.actions.get(A.OPEN_RESULTS)) if self.actions is not None else None
        self.save = self._save_button()
        file_widgets = tuple(widget for widget in (open_button, self.save) if widget is not None)
        layout.addWidget(ResultRibbonGroup("FILE", file_widgets))
        self.mesh_lines = ribbon_button("Mesh Lines", IconKind.MESH_LINES, True)
        self.boundary_lines = ribbon_button("Boundary", IconKind.BOUNDARY_LINES, True)
        self.deform = ResultDeformationButton()
        self.undeformed = ribbon_button("Undeformed", IconKind.UNDEFORMED, False, 82)
        self.section = ResultSectionButton()
        layout.addWidget(ResultRibbonGroup("VISUALS", (self.mesh_lines, self.boundary_lines, self.deform, self.undeformed, self.section)))
        self.range = ResultRangeButton(); layout.addWidget(ResultRibbonGroup("CONTOUR", (self.range,)))
        self.choose = ResultFieldButton(); layout.addWidget(ResultRibbonGroup("FIELD", (self.choose,)))
        self.query_nodes = ribbon_button("Query Nodes", IconKind.QUERY_NODE, False, 82)
        self.query_elements = ribbon_button("Query Elements", IconKind.QUERY_ELEMENT, False, 88)
        layout.addWidget(ResultRibbonGroup("QUERY", (self.query_nodes, self.query_elements))); layout.addStretch(1)
        for button in (self.mesh_lines, self.boundary_lines, self.undeformed): button.toggled.connect(self._emit)
        self.section.settings_changed.connect(self._emit)
        self.deform.settings_changed.connect(self._emit); self.deform.auto_requested.connect(self._auto_deformation_scale); self.range.range_changed.connect(self._emit)
        self.choose.selection_changed.connect(self._field_changed); self._wire_queries()

    def _save_button(self):
        button = QToolButton(); button.setText("Save Results"); button.setIcon(make_icon(IconKind.SAVE, 28)); button.setIconSize(QSize(28, 28))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon); button.setProperty("ribbonButton", True); button.setFixedSize(82, 70)
        button.clicked.connect(self._save_results); button.setEnabled(False); return button

    def _wire_queries(self):
        group = QButtonGroup(self); group.setExclusive(False); group.addButton(self.query_nodes); group.addButton(self.query_elements); self.query_group = group
        self.query_nodes.toggled.connect(lambda checked: self._query_toggled(self.query_nodes, self.query_elements, checked))
        self.query_elements.toggled.connect(lambda checked: self._query_toggled(self.query_elements, self.query_nodes, checked))

    def set_solution(self, result, field=None):
        if getattr(result, "id", None) != getattr(self.result, "id", None):
            self.section.reset_for_result()
        self.result = result; fields = self.loader.fields(result.source_file) if result and result.source_file else []
        self.save.setEnabled(bool(result and result.source_file)); self.choose.set_solution(result, fields, field)

    def set_section_state(self, state):
        self.section.set_state(state)

    def _field_changed(self):
        field = self.choose.current_field()
        if self.result and field: self.range.set_data_range(*self.loader.scalar_range(self.result.source_file, field))
        self._emit()

    def _query_toggled(self, current, other, checked):
        if checked: other.blockSignals(True); other.setChecked(False); other.blockSignals(False)
        self._emit()

    def _save_results(self):
        if not self.result or not self.result.source_file: return
        source = Path(self.result.source_file); target, _ = QFileDialog.getSaveFileName(self, "Save Results", source.name, "FRD results (*.frd)")
        if not target: return
        destination = Path(target); destination = destination if destination.suffix else destination.with_suffix(".frd")
        try:
            if source.resolve() != destination.resolve(): copy2(source, destination)
        except Exception as exc: QMessageBox.warning(self, "Save Results", str(exc))

    def _auto_deformation_scale(self):
        value = auto_deformation_scale(self.result, self.choose.current_field())
        if value is None:
            QMessageBox.information(self, "Deformation scale", "No displacement field is available for automatic scaling.")
            return
        self.deform.set_scale(value)

    def _emit(self, *_):
        field = self.choose.current_field(); deform, scale = self.deform.values()
        query = "node" if self.query_nodes.isChecked() else "element" if self.query_elements.isChecked() else ""
        options = {"mesh_lines": self.mesh_lines.isChecked(), "boundary_lines": self.boundary_lines.isChecked(),
                   "deform": deform, "undeformed": self.undeformed.isChecked(), "scale": scale,
                   "query": query, "range": self.range.values(), "selection": self.choose.labels(),
                   "section": self.section.values()}
        if self.result: self.result_requested.emit(self.result, field, options)


def create(actions=None, *_): return ResultsPage(actions)
def groups(): return ()
