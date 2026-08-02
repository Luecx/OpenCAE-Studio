from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractItemView, QFormLayout, QFrame, QHeaderView, QLabel, QSizePolicy, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from opencae.ui.core.theme import PALETTE
from .result_query_model import QueryResult
from .result_selection_panel import RESULT_INFO_WIDTH


class ResultQueryPanel(QFrame):
    def __init__(self,parent=None):
        super().__init__(parent); self.setObjectName("ResultQueryPanel"); self.setFixedWidth(RESULT_INFO_WIDTH); self.setSizePolicy(QSizePolicy.Policy.Fixed,QSizePolicy.Policy.Fixed); self.hide()
        self.setStyleSheet(f"QFrame#ResultQueryPanel{{background:{PALETTE['panel']};border:1px solid {PALETTE['border_light']};border-radius:7px;}}")
        layout=QVBoxLayout(self); layout.setContentsMargins(12,10,12,10); layout.setSpacing(7); self.title=QLabel("Result Query"); self.title.setObjectName("PanelTitle"); layout.addWidget(self.title)
        self.body=QWidget(); self.form=QFormLayout(self.body); self.form.setContentsMargins(0,0,0,0); self.form.setHorizontalSpacing(12); self.form.setVerticalSpacing(5); layout.addWidget(self.body)
        self.table=QTableWidget(); self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.verticalHeader().setVisible(False); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.table.hide(); layout.addWidget(self.table)

    def show_prompt(self,mode):
        noun="node" if mode=="node" else "element"; self.show_result(f"Query {noun.title()}",QueryResult(summary=[("Selection",f"Click a {noun} in the mesh")]))

    def show_result(self,title,result):
        self.title.setText(title); self._clear(); rows=result.summary or [("Result","No values available for this selection")]
        for key,value in rows:
            name=QLabel(str(key)); name.setStyleSheet(f"color:{PALETTE['muted']};"); text=QLabel(str(value)); text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse); text.setWordWrap(True); self.form.addRow(name,text)
        if result.matrix:self._show_matrix(result.columns,result.matrix)
        self.layout().activate(); self.adjustSize(); self.setFixedHeight(self.sizeHint().height()); self.show(); self.raise_()

    def _show_matrix(self,columns,values):
        self.table.setColumnCount(len(columns)); self.table.setHorizontalHeaderLabels(columns); self.table.setRowCount(len(values))
        for row,items in enumerate(values):
            for column,value in enumerate(items): self.table.setItem(row,column,QTableWidgetItem(str(value)))
        self.table.resizeRowsToContents(); row_height=sum(max(24,self.table.rowHeight(row)) for row in range(len(values)))
        self.table.setFixedHeight(self.table.horizontalHeader().height()+row_height+2*self.table.frameWidth()+2); self.table.show()

    def clear_query(self):self._clear(); self.hide()
    def _clear(self):
        self.setMinimumHeight(0); self.setMaximumHeight(16777215)
        while self.form.rowCount():self.form.removeRow(0)
        self.table.clearContents(); self.table.setRowCount(0); self.table.hide()
