from __future__ import annotations
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QFormLayout,QLabel,QLineEdit,QComboBox,QDoubleSpinBox,QTreeWidget,QTreeWidgetItem,QWidget,QVBoxLayout,QTabWidget,QPlainTextEdit,QTableWidget,QTableWidgetItem,QHeaderView)
from opencae.core.model import ProjectModel
from .theme import PALETTE

class ProjectTree(QTreeWidget):
    selectionLabelChanged=pyqtSignal(str)
    def __init__(self, model:ProjectModel,parent=None):
        super().__init__(parent); self.model=model; self.setHeaderHidden(True); self.setAlternatingRowColors(True); self.populate(); self.itemSelectionChanged.connect(self._changed)
    def populate(self):
        self.clear(); root=QTreeWidgetItem([self.model.name]); root.setExpanded(True); self.addTopLevelItem(root)
        parts=QTreeWidgetItem(['Parts']); root.addChild(parts); parts.setExpanded(True)
        for p in self.model.parts:
            i=QTreeWidgetItem([p.name]); parts.addChild(i)
            for label in ['Geometry',f'Mesh ({p.element_type})','Regions','Section Assignments']: i.addChild(QTreeWidgetItem([label]))
        ass=QTreeWidgetItem(['Assembly']); root.addChild(ass); ass.setExpanded(True)
        for i in self.model.instances: ass.addChild(QTreeWidgetItem([i.name]))
        bcs=QTreeWidgetItem(['Boundary Conditions']); root.addChild(bcs)
        for x in self.model.boundary_conditions: bcs.addChild(QTreeWidgetItem([x.name]))
        loads=QTreeWidgetItem(['Loads']); root.addChild(loads)
        for x in self.model.loads: loads.addChild(QTreeWidgetItem([x.name]))
        analyses=QTreeWidgetItem(['Analyses']); root.addChild(analyses); analyses.setExpanded(True)
        for x in self.model.analyses: analyses.addChild(QTreeWidgetItem([x.name]))
        root.addChild(QTreeWidgetItem(['Results']))
        parts.child(0).setSelected(True)
    def _changed(self):
        items=self.selectedItems();
        if items:self.selectionLabelChanged.emit(items[0].text(0))

class PropertiesPanel(QWidget):
    def __init__(self,model:ProjectModel,parent=None):
        super().__init__(parent); self.model=model; lay=QVBoxLayout(self); lay.setContentsMargins(8,8,8,8)
        self.title=QLabel('Bracket'); self.title.setStyleSheet(f'font-size:13pt;font-weight:600;color:{PALETTE["text"]};padding-bottom:6px;'); lay.addWidget(self.title)
        form=QFormLayout(); form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft); form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        p=model.active_part(); self.name=QLineEdit(p.name); self.material=QComboBox(); self.material.addItems(['Aluminum 6061-T6','Steel S355','Titanium Ti-6Al-4V']); self.section=QComboBox(); self.section.addItems(['Solid Section','Shell 2 mm','Beam Section']); self.mesh=QComboBox(); self.mesh.addItems(['Default','Coarse','Fine']); self.etype=QComboBox(); self.etype.addItems(['C3D10','C3D8R','S4','B33']); self.size=QDoubleSpinBox(); self.size.setRange(.01,1e6); self.size.setValue(p.global_size); self.size.setSuffix(' mm')
        for a,b in [('Name',self.name),('Material',self.material),('Section',self.section),('Mesh Variant',self.mesh),('Element Type',self.etype),('Global Size',self.size)]: form.addRow(a,b)
        form.addRow('Nodes',QLabel(f'{p.nodes:,}')); form.addRow('Elements',QLabel(f'{p.elements:,}'))
        lay.addLayout(form); lay.addStretch()
    def show_selection(self,text:str): self.title.setText(text)

class BottomPanel(QTabWidget):
    def __init__(self,parent=None):
        super().__init__(parent); self.setMinimumHeight(165)
        self.log=QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumBlockCount(2000); self.addTab(self.log,'Log')
        self.jobs=QTableWidget(0,5); self.jobs.setHorizontalHeaderLabels(['Job','Analysis','Solver','Status','Progress']); self.jobs.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); self.addTab(self.jobs,'Jobs')
        self.solver=QPlainTextEdit(); self.solver.setReadOnly(True); self.addTab(self.solver,'Solver')
        self.console=QPlainTextEdit(); self.console.setPlaceholderText('Embedded Python console placeholder\n>>> project.parts[0].name'); self.addTab(self.console,'Python Console')
        self.append_log('OpenCAE Studio started.'); self.append_log('Project loaded: Bracket Study')
    def append_log(self,msg:str): self.log.appendPlainText(msg)
    def add_job(self,name,analysis,solver,status='Prepared',progress='0%'):
        r=self.jobs.rowCount(); self.jobs.insertRow(r)
        for c,v in enumerate([name,analysis,solver,status,progress]): self.jobs.setItem(r,c,QTableWidgetItem(v))
