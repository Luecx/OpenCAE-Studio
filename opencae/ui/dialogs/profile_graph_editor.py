from PyQt6.QtWidgets import QHBoxLayout,QHeaderView,QLabel,QPushButton,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget


class GraphProfileEditor(QWidget):
    def __init__(self,nodes="",segments="",length_unit="",parent=None):
        super().__init__(parent); root=QHBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(12)
        y_header=f"y [{length_unit}]" if length_unit else "y"; z_header=f"z [{length_unit}]" if length_unit else "z"
        thickness_header=f"Thickness [{length_unit}]" if length_unit else "Thickness"
        self.nodes=self._table(("ID",y_header,z_header)); self.segments=self._table(("Node 1","Node 2",thickness_header))
        root.addWidget(self._pane("Local nodes",self.nodes,self._add_node)); root.addWidget(self._pane("Segments",self.segments,self._add_segment))
        self._load(self.nodes,nodes,3); self._load(self.segments,segments,3)
    @staticmethod
    def _table(headers):
        table=QTableWidget(0,len(headers)); table.setHorizontalHeaderLabels(headers); table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); table.setMinimumHeight(220); return table
    def _pane(self,title,table,add):
        pane=QWidget(); layout=QVBoxLayout(pane); layout.setContentsMargins(0,0,0,0); layout.addWidget(QLabel(title)); layout.addWidget(table)
        row=QHBoxLayout(); plus=QPushButton("+"); minus=QPushButton("−"); plus.setFixedWidth(34); minus.setFixedWidth(34); plus.clicked.connect(add); minus.clicked.connect(lambda:self._remove(table)); row.addWidget(plus); row.addWidget(minus); row.addStretch(1); layout.addLayout(row); return pane
    def _add_node(self):self._append(self.nodes,(self.nodes.rowCount()+1,0.0,0.0))
    def _add_segment(self):self._append(self.segments,(1,2,1.0))
    @staticmethod
    def _append(table,values):
        row=table.rowCount(); table.insertRow(row)
        for column,value in enumerate(values):table.setItem(row,column,QTableWidgetItem(str(value)))
    @staticmethod
    def _remove(table):
        rows=sorted({index.row() for index in table.selectedIndexes()},reverse=True)
        if not rows and table.rowCount():rows=[table.rowCount()-1]
        for row in rows:table.removeRow(row)
    def _load(self,table,text,width):
        for line in str(text).replace(";","\n").splitlines():
            values=[item.strip() for item in line.split(",")]
            if len(values)==width:self._append(table,values)
        if not table.rowCount():self._append(table,(1,0,0) if table is self.nodes else (1,2,1.0))
    @staticmethod
    def _text(table):
        return "\n".join(",".join(table.item(row,column).text().strip() if table.item(row,column) else "" for column in range(table.columnCount())) for row in range(table.rowCount()))
    def values(self):return {"nodes":self._text(self.nodes),"segments":self._text(self.segments)}
    def connect_changed(self,callback):
        self.nodes.itemChanged.connect(callback); self.segments.itemChanged.connect(callback)
