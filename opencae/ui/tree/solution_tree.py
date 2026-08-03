import logging

_LOG = logging.getLogger(__name__)
from PyQt6.QtCore import QSize,Qt,pyqtSignal
from PyQt6.QtGui import QStandardItem,QStandardItemModel
from PyQt6.QtWidgets import QTreeView
from opencae.results import FrdLoader
from opencae.results.navigation import display_field,fields_for,frame_keys,frame_label,step_ids,step_label
from opencae.ui.core.icon_factory import IconKind,make_icon
from .branch_style import TreeBranchStyle

class SolutionTree(QTreeView):
    solution_requested=pyqtSignal(object,object)
    def __init__(self,store,parent=None):
        super().__init__(parent); self.store=store; self.setHeaderHidden(True); self.setUniformRowHeights(True); self.setAnimated(True)
        self.setIndentation(18); self.setIconSize(QSize(18,18)); self.setStyle(TreeBranchStyle(self.style()))
        self.clicked.connect(self._clicked); self.expanded.connect(self._exclusive_expand); store.changed.connect(self.rebuild); self.rebuild()
    def rebuild(self,*_):
        model=QStandardItemModel(); model.setHorizontalHeaderLabels(["Solutions"]); root=model.invisibleRootItem(); loader=FrdLoader()
        for result in self.store.project.results:
            if result.source_file:
                try:
                    result.fields = loader.fields(result.source_file)
                except (OSError, RuntimeError, TypeError, ValueError) as exc:
                    _LOG.warning("Could not load result tree from %s: %s", result.source_file, exc)
                    self.store.message.emit(f"Could not load results '{result.name}': {exc}")
            result_item=self._item(result.name,result,None,IconKind.RESULTS); root.appendRow(result_item)
            for step_index,step_id in enumerate(step_ids(result.fields)):
                step=self._item(step_label(result,step_id,step_index),result,None,IconKind.RESULT_STEP); result_item.appendRow(step)
                for frame_id,value in frame_keys(result.fields,step_id):
                    frame=self._item(frame_label(frame_id,value),result,None,IconKind.RESULT_FRAME); step.appendRow(frame)
                    for field in fields_for(result.fields,step_id,frame_id):
                        block=self._item(field.name,result,display_field(field,"Magnitude"),IconKind.FIELD); frame.appendRow(block)
                        for component in (*field.metadata.get("components",()),*field.metadata.get("derived",())):
                            block.appendRow(self._item(component,result,display_field(field,component),IconKind.CONTOUR))
        self.setModel(model); self.collapseAll(); self._expand_first_chain()
    def _expand_first_chain(self):
        index=self.model().index(0,0)
        while index.isValid():self.expand(index); index=self.model().index(0,0,index)
    def _exclusive_expand(self,index):
        parent=index.parent(); rows=self.model().rowCount(parent)
        for row in range(rows):
            sibling=self.model().index(row,0,parent)
            if sibling!=index:self.collapse(sibling)
    @staticmethod
    def _item(text,result,field,icon):
        item=QStandardItem(make_icon(icon,18),text); item.setEditable(False); item.setData(result,Qt.ItemDataRole.UserRole); item.setData(field,Qt.ItemDataRole.UserRole+1); return item
    def _clicked(self,index):
        result=index.data(Qt.ItemDataRole.UserRole); field=index.data(Qt.ItemDataRole.UserRole+1)
        if result is not None:self.solution_requested.emit(result,field)
