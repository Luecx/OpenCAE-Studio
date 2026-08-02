from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout


class StepCollectorsDialog(QDialog):
    def __init__(self, steps, loads, supports, parent=None):
        super().__init__(parent); self.steps=steps; self.loads=loads; self.supports=supports
        self.setWindowTitle("Step Load / Support Matrix"); self.resize(920,560)
        root=QVBoxLayout(self); root.addWidget(QLabel("Check which collectors are active in each step."))
        self.table=QTableWidget(len(supports)+len(loads),len(steps)+1); self.table.setHorizontalHeaderLabels(("Collector",*[s.name for s in steps]))
        rows=[("Support",name) for name in supports]+[("Load",name) for name in loads]
        for row,(kind,name) in enumerate(rows):
            self.table.setItem(row,0,QTableWidgetItem(f"{kind}: {name}"))
            for col,step in enumerate(steps,1): self._cell(row,col,kind,name,step)
        self.table.resizeColumnsToContents(); root.addWidget(self.table,1)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); root.addWidget(buttons)

    def _cell(self,row,col,kind,name,step):
        item=QTableWidgetItem(); item.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsUserCheckable)
        enabled=kind=="Support" or step.uses_loads
        if not enabled:item.setFlags(Qt.ItemFlag.NoItemFlags)
        selected=name in (step.active_supports if kind=="Support" else step.active_loads)
        item.setCheckState(Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked); self.table.setItem(row,col,item)

    def apply(self):
        for col,step in enumerate(self.steps,1):
            step.active_supports=[name for row,name in enumerate(self.supports) if self._checked(row,col)]
            offset=len(self.supports); step.active_loads=[name for i,name in enumerate(self.loads) if step.uses_loads and self._checked(offset+i,col)]

    def _checked(self,row,col):
        item=self.table.item(row,col); return item is not None and item.checkState()==Qt.CheckState.Checked
