from __future__ import annotations
import json, sys, tempfile
from pathlib import Path
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QApplication,QDockWidget,QFileDialog,QLabel,QMainWindow,QMessageBox,QToolBar,QWidget,QVBoxLayout
from opencae.core.model import ProjectModel
from opencae.solvers.registry import available_solvers
from opencae.ui.panels import BottomPanel,ProjectTree,PropertiesPanel
from opencae.ui.ribbon import Ribbon
from opencae.ui.theme import stylesheet,PALETTE
from opencae.ui.viewport import Viewport

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.model=ProjectModel(); self.solvers=available_solvers(); self.current_solver='FEMaster'
        self.setWindowTitle('OpenCAE Studio — Bracket Study'); self.resize(1600,980); self.setDockOptions(QMainWindow.DockOption.AllowNestedDocks|QMainWindow.DockOption.AllowTabbedDocks|QMainWindow.DockOption.AnimatedDocks)
        self._actions={}; self._build_actions(); self._build_menus(); self._build_central(); self._build_docks(); self._build_status(); self._connect();
    def _act(self,key,text,slot=None,shortcut=None,checkable=False):
        a=QAction(text,self); a.setCheckable(checkable)
        if slot:a.triggered.connect(slot)
        if shortcut:a.setShortcut(QKeySequence(shortcut))
        self._actions[key]=a; return a
    def _build_actions(self):
        self._act('new','New Project',self.new_project,'Ctrl+N'); self._act('open','Open Project…',self.open_project,'Ctrl+O'); self._act('save','Save Project',self.save_project,'Ctrl+S'); self._act('saveas','Save Project As…',lambda:self.save_project(True),'Ctrl+Shift+S'); self._act('import','Import Geometry…',lambda:self.command('PART','Import')); self._act('export','Export Input Deck…',self.write_deck); self._act('quit','Quit',self.close,'Ctrl+Q')
        self._act('undo','Undo','', 'Ctrl+Z'); self._act('redo','Redo','', 'Ctrl+Y'); self._act('cut','Cut'); self._act('copy','Copy'); self._act('paste','Paste'); self._act('delete','Delete','', 'Delete'); self._act('selectall','Select All','', 'Ctrl+A')
        self._act('fit','Fit View',self.viewport_fit if hasattr(self,'viewport') else None,'F'); self._act('dark','Dark Theme',checkable=True); self._actions['dark'].setChecked(True)
        self._act('run','Run Active Analysis',self.run_active,'F5'); self._act('validate','Validate Model',lambda:self.command('SOLVE','Check Model'),'F7'); self._act('about','About',self.about)
    def _build_menus(self):
        file=self.menuBar().addMenu('&File');
        for k in ['new','open','save','saveas']: file.addAction(self._actions[k])
        file.addSeparator(); file.addAction(self._actions['import']); file.addAction(self._actions['export']); file.addSeparator(); file.addAction(self._actions['quit'])
        edit=self.menuBar().addMenu('&Edit');
        for k in ['undo','redo']: edit.addAction(self._actions[k])
        edit.addSeparator();
        for k in ['cut','copy','paste','delete','selectall']: edit.addAction(self._actions[k])
        view=self.menuBar().addMenu('&View'); view.addAction('Fit View',lambda:self.viewport.fit_view()); view.addAction('Toggle Mesh',lambda:self.viewport.toggle_mesh()); view.addAction('Toggle Contour',lambda:self.viewport.toggle_contour()); view.addSeparator(); view.addAction(self._actions['dark'])
        tools=self.menuBar().addMenu('&Tools'); tools.addAction('Command Palette…',lambda:self.bottom.append_log('Command palette opened.')); tools.addAction('Preferences…',lambda:self.bottom.append_log('Preferences opened.')); tools.addAction('Plugin Manager…',lambda:self.bottom.append_log('Plugin manager opened.'))
        solver=self.menuBar().addMenu('&Solver');
        for name in self.solvers: solver.addAction(name,lambda checked=False,n=name:self.select_solver(n))
        solver.addSeparator(); solver.addAction(self._actions['validate']); solver.addAction(self._actions['run'])
        window=self.menuBar().addMenu('&Window'); window.addAction('Reset Layout',self.reset_layout); window.addAction('Save Layout',lambda:self.bottom.append_log('Layout saved.'))
        helpm=self.menuBar().addMenu('&Help'); helpm.addAction('Documentation'); helpm.addAction('Keyboard Shortcuts'); helpm.addSeparator(); helpm.addAction(self._actions['about'])
    def _build_central(self):
        container=QWidget(); lay=QVBoxLayout(container); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0); self.ribbon=Ribbon(); self.viewport=Viewport(); lay.addWidget(self.ribbon); lay.addWidget(self.viewport,1); self.setCentralWidget(container)
    def _dock(self,title,widget,area):
        d=QDockWidget(title,self); d.setObjectName(title.replace(' ','')); d.setWidget(widget); self.addDockWidget(area,d); return d
    def _build_docks(self):
        self.tree=ProjectTree(self.model); self.properties=PropertiesPanel(self.model); self.bottom=BottomPanel(); self.project_dock=self._dock('Project',self.tree,Qt.DockWidgetArea.LeftDockWidgetArea); self.properties_dock=self._dock('Properties',self.properties,Qt.DockWidgetArea.RightDockWidgetArea); self.bottom_dock=self._dock('Output',self.bottom,Qt.DockWidgetArea.BottomDockWidgetArea); self.project_dock.setMinimumWidth(250); self.properties_dock.setMinimumWidth(300)
    def _build_status(self):
        self.statusBar().showMessage('Ready'); self.unit=QLabel('Unit System: mm, N, MPa   |   Solver: FEMaster'); self.statusBar().addPermanentWidget(self.unit)
    def _connect(self):
        self.ribbon.commandTriggered.connect(self.command); self.ribbon.stageChanged.connect(lambda s:self.statusBar().showMessage(f'{s.title()} workspace')); self.tree.selectionLabelChanged.connect(self.properties.show_selection); self.viewport.selectionChanged.connect(self.bottom.append_log)
    def command(self,stage,command):
        self.bottom.append_log(f'[{stage}] {command}'); self.statusBar().showMessage(command,3000)
        if command=='Generate': self.bottom.append_log('Mesh generation completed: 241,890 nodes, 152,624 elements.')
        elif command=='Write Deck': self.write_deck()
        elif command=='Run Active': self.run_active()
        elif command=='Contour': self.viewport.toggle_contour()
    def select_solver(self,name): self.current_solver=name; self.unit.setText(f'Unit System: mm, N, MPa   |   Solver: {name}'); self.bottom.append_log(f'Active solver changed to {name}.')
    def write_deck(self):
        analysis=self.model.analyses[0]; path,_=QFileDialog.getSaveFileName(self,'Export Input Deck',f'{analysis.name}.inp','Input decks (*.inp);;All files (*)')
        if not path:return
        deck=self.solvers[self.current_solver].write_deck(self.model,analysis,Path(path)); self.bottom.append_log(f'Deck written: {deck}'); self.bottom.solver.setPlainText(deck.read_text(encoding='utf-8')); self.bottom.setCurrentWidget(self.bottom.solver)
    def run_active(self):
        analysis=self.model.analyses[0]; work=Path(tempfile.mkdtemp(prefix='opencae_')); run=self.solvers[self.current_solver].prepare_run(self.model,analysis,work); self.bottom.add_job(run.input_file.stem,analysis.name,self.current_solver,'Prepared','0%'); self.bottom.append_log('Prepared solver run: '+' '.join(run.command)); self.bottom.solver.setPlainText(run.input_file.read_text(encoding='utf-8')); self.bottom.setCurrentWidget(self.bottom.jobs); QMessageBox.information(self,'Solver run prepared','The input deck and command were prepared.\n\n'+str(run.input_file)+'\n\nCommand:\n'+' '.join(run.command)+'\n\nExecution is intentionally not started in the dummy prototype.')
    def save_project(self,save_as=False):
        path=self.model.path
        if save_as or path is None:
            s,_=QFileDialog.getSaveFileName(self,'Save Project',str(path or Path.cwd()/'bracket.ocae'),'OpenCAE project (*.ocae)');
            if not s:return
            path=Path(s); self.model.path=path
        data={'name':self.model.name,'unit_system':self.model.unit_system,'solver':self.current_solver,'parts':[p.name for p in self.model.parts],'instances':[i.name for i in self.model.instances]}; path.write_text(json.dumps(data,indent=2),encoding='utf-8'); self.bottom.append_log(f'Project saved: {path}')
    def open_project(self):
        s,_=QFileDialog.getOpenFileName(self,'Open Project','','OpenCAE project (*.ocae);;All files (*)');
        if s:self.bottom.append_log(f'Opened project placeholder: {s}')
    def new_project(self): self.bottom.append_log('New project created (dummy).')
    def reset_layout(self): self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea,self.project_dock); self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,self.properties_dock); self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea,self.bottom_dock)
    def about(self): QMessageBox.about(self,'About OpenCAE Studio','OpenCAE Studio\nPyQt6 UI concept\nDeck-based multi-solver architecture')

def run():
    app=QApplication(sys.argv); app.setApplicationName('OpenCAE Studio'); app.setOrganizationName('OpenCAE'); app.setStyleSheet(stylesheet()); w=MainWindow(); w.show(); return app.exec()
