from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog,QDoubleSpinBox,QFormLayout,QLabel,QLineEdit,QMessageBox,QStackedWidget,QVBoxLayout,QWidget

from opencae.ui.core.controls import dialog_buttons
from opencae.ui.core.widgets import ChevronComboBox,PointSelectionWidget,SelectionMembersWidget

PARTITION_TYPES=('Cell by plane','Face by two points','Edge at parameter','Edge at vertex')

class PartitionDialog(QDialog):
    def __init__(self,selection_provider,point_provider,feature=None,parent=None):
        super().__init__(parent); self.selection_provider=selection_provider; self.point_provider=point_provider; self.feature=feature; self.setWindowTitle('Edit Partition' if feature else 'Create Partition'); self.setMinimumWidth(660); self.setWindowModality(Qt.WindowModality.NonModal)
        root=QVBoxLayout(self); root.setContentsMargins(18,16,18,14); root.setSpacing(12); title=QLabel(self.windowTitle()); title.setObjectName('PanelTitle'); root.addWidget(title)
        form=QFormLayout(); self.name=QLineEdit(getattr(feature,'name','Partition-1')); self.kind=ChevronComboBox(); self.kind.addItems(PARTITION_TYPES); self.kind.setCurrentText(self._kind_from_feature(feature)); form.addRow('History feature',self.name); form.addRow('Partition method',self.kind); root.addLayout(form)
        self.stack=QStackedWidget(); root.addWidget(self.stack); self._build_pages(); self.kind.currentIndexChanged.connect(self.stack.setCurrentIndex); self.stack.setCurrentIndex(PARTITION_TYPES.index(self.kind.currentText())); self._load(feature)
        help_text=QLabel('The dialog is modeless: select entities in the viewport with left click, use Shift for multiple selection, then press “Use current selection”.'); help_text.setWordWrap(True); help_text.setObjectName('MutedText'); root.addWidget(help_text)
        buttons=dialog_buttons(); buttons.accepted.connect(self._accept); buttons.rejected.connect(self.reject); root.addWidget(buttons)
    def _members(self,dimension):
        return [item for item in self.selection_provider(dimension)]
    def _selector(self,dimension):return SelectionMembersWidget(selection_provider=lambda:self._members(dimension))
    def _build_pages(self):
        plane=QWidget(); layout=QVBoxLayout(plane); layout.addWidget(QLabel('Target cells')); self.plane_targets=self._selector(3); layout.addWidget(self.plane_targets); form=QFormLayout(); self.origin=[self._number(0.0) for _ in range(3)]; self.normal=[self._number(v) for v in (1.0,0.0,0.0)]; form.addRow('Plane origin X',self.origin[0]); form.addRow('Plane origin Y',self.origin[1]); form.addRow('Plane origin Z',self.origin[2]); form.addRow('Plane normal X',self.normal[0]); form.addRow('Plane normal Y',self.normal[1]); form.addRow('Plane normal Z',self.normal[2]); layout.addLayout(form); self.stack.addWidget(plane)
        face=QWidget(); layout=QVBoxLayout(face); layout.addWidget(QLabel('Target face')); self.face_targets=self._selector(2); layout.addWidget(self.face_targets); layout.addWidget(QLabel('Two picked points defining the partition line')); self.face_points=PointSelectionWidget(selection_provider=self.point_provider); layout.addWidget(self.face_points); self.stack.addWidget(face)
        edge_parameter=QWidget(); layout=QVBoxLayout(edge_parameter); layout.addWidget(QLabel('Target edge')); self.edge_parameter_targets=self._selector(1); layout.addWidget(self.edge_parameter_targets); form=QFormLayout(); self.fraction=self._number(0.5); self.fraction.setRange(0.000001,0.999999); form.addRow('Normalized parameter',self.fraction); layout.addLayout(form); self.stack.addWidget(edge_parameter)
        edge_vertex=QWidget(); layout=QVBoxLayout(edge_vertex); layout.addWidget(QLabel('Target edge')); self.edge_vertex_targets=self._selector(1); layout.addWidget(self.edge_vertex_targets); layout.addWidget(QLabel('Splitting vertex')); self.edge_vertex=self._selector(0); layout.addWidget(self.edge_vertex); self.stack.addWidget(edge_vertex)
    @staticmethod
    def _number(value):editor=QDoubleSpinBox(); editor.setRange(-1e30,1e30); editor.setDecimals(8); editor.setValue(value); return editor
    @staticmethod
    def _kind_from_feature(feature):
        if feature is None:return PARTITION_TYPES[0]
        if feature.feature_type=='Partition Face':return PARTITION_TYPES[1]
        if feature.feature_type=='Partition Edge':return PARTITION_TYPES[3] if feature.parameters.get('method')=='Vertex' else PARTITION_TYPES[2]
        return PARTITION_TYPES[0]
    def _load(self,feature):
        if feature is None:return
        kind=self._kind_from_feature(feature)
        if kind==PARTITION_TYPES[0]:
            self.plane_targets.set_members(feature.references); origin=feature.parameters.get('origin',(0,0,0)); normal=feature.parameters.get('normal',(1,0,0)); [self.origin[i].setValue(origin[i]) for i in range(3)]; [self.normal[i].setValue(normal[i]) for i in range(3)]
        elif kind==PARTITION_TYPES[1]:self.face_targets.set_members(feature.references); self.face_points.set_points(feature.parameters.get('points',()))
        elif kind==PARTITION_TYPES[2]:self.edge_parameter_targets.set_members(feature.references); self.fraction.setValue(feature.parameters.get('fraction',0.5))
        else:self.edge_vertex_targets.set_members(feature.references); self.edge_vertex.set_members(feature.parameters.get('vertices',()))
    def _accept(self):
        values=self.values()
        if not values['name']:QMessageBox.warning(self,'Invalid partition','Enter a feature name.'); return
        required=(1 if values['partition_type']!='Cell by plane' else 1)
        if len(values['references'])<required:QMessageBox.warning(self,'Missing target','Capture the target geometry first.'); return
        if values['partition_type']=='Face by two points' and len(values['parameters']['points'])!=2:QMessageBox.warning(self,'Missing points','Pick exactly two points on the target face.'); return
        if values['partition_type']=='Edge at vertex' and len(values['parameters']['vertices'])!=1:QMessageBox.warning(self,'Missing vertex','Select exactly one vertex.'); return
        self.accept()
    def values(self):
        kind=self.kind.currentText(); base={'name':self.name.text().strip(),'partition_type':kind}
        if kind==PARTITION_TYPES[0]:base.update(references=self.plane_targets.members(),parameters={'origin':tuple(e.value() for e in self.origin),'normal':tuple(e.value() for e in self.normal)})
        elif kind==PARTITION_TYPES[1]:base.update(references=self.face_targets.members(),parameters={'points':self.face_points.points()})
        elif kind==PARTITION_TYPES[2]:base.update(references=self.edge_parameter_targets.members(),parameters={'method':'Parameter','fraction':self.fraction.value()})
        else:base.update(references=self.edge_vertex_targets.members(),parameters={'method':'Vertex','vertices':self.edge_vertex.members()})
        return base
