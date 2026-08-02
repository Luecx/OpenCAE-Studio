from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout,QListWidget,QPushButton,QVBoxLayout,QWidget

class PointSelectionWidget(QWidget):
    def __init__(self,points=(),selection_provider=None,parent=None):
        super().__init__(parent); self._provider=selection_provider; self._points=[]; self.list=QListWidget(); self.list.setMinimumHeight(82); self.set_points(points)
        capture=QPushButton('Use current point selection'); capture.clicked.connect(self.capture); clear=QPushButton('Clear'); clear.clicked.connect(lambda:self.set_points(())); row=QHBoxLayout(); row.addWidget(capture); row.addWidget(clear); row.addStretch(1)
        layout=QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.addWidget(self.list); layout.addLayout(row)
    def capture(self):
        if self._provider is not None:self.set_points(self._provider() or ())
    def set_points(self,points):
        self._points=[tuple(map(float,p)) for p in points]; self.list.clear()
        for i,p in enumerate(self._points,1):self.list.addItem(f'Point {i}: ({p[0]:.6g}, {p[1]:.6g}, {p[2]:.6g})')
    def points(self):return list(self._points)
