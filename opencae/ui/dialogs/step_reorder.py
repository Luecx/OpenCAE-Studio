from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QListWidget, QPushButton, QVBoxLayout


class StepReorderDialog(QDialog):
    def __init__(self, names, parent=None):
        super().__init__(parent); self.setWindowTitle("Reorder Steps"); self.resize(430,420)
        root=QVBoxLayout(self); self.list=QListWidget(); self.list.addItems(names); root.addWidget(self.list)
        up=QPushButton("Move Up"); down=QPushButton("Move Down"); up.clicked.connect(lambda:self._move(-1)); down.clicked.connect(lambda:self._move(1))
        root.addWidget(up); root.addWidget(down)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); root.addWidget(buttons)

    def _move(self, offset):
        row=self.list.currentRow(); target=row+offset
        if row<0 or target<0 or target>=self.list.count():return
        item=self.list.takeItem(row); self.list.insertItem(target,item); self.list.setCurrentRow(target)

    def order(self): return [self.list.item(i).text() for i in range(self.list.count())]
