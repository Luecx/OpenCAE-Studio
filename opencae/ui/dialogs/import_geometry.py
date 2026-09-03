from pathlib import Path

from PyQt6.QtWidgets import QMessageBox

from opencae.ui.core.fields import FieldSpec
from opencae.ui.core.form_dialog import FormDialog


class ImportGeometryDialog(FormDialog):
    def __init__(self,active_part=None,feature=None,existing_names=(),parent=None,default_part_name="Part-1",default_feature_name="Import Geometry-1"):
        self.active_part=active_part; self.existing_names={name.casefold() for name in existing_names}
        current_file=str(getattr(feature, 'source_file', '')) if feature else ''
        part_name=active_part.name if active_part else default_part_name
        if active_part and active_part.geometry and feature is None:part_name=default_part_name
        settings=active_part.geometry_settings if active_part else None
        super().__init__('Import OpenCASCADE Geometry',(
            FieldSpec('part_name','Part name','text',part_name), FieldSpec('name','History feature','text',feature.name if feature else default_feature_name),
            FieldSpec('file','STEP / IGES / BREP file','file',current_file,file_filter='CAD geometry (*.step *.stp *.iges *.igs *.brep);;All files (*.*)'),
            FieldSpec('heal','Heal imported shape','bool',getattr(settings,'heal_on_import',True)), FieldSpec('sew_faces','Sew adjacent faces','bool',getattr(settings,'sew_faces',True)),
            FieldSpec('make_solids','Create solids from shells','bool',getattr(settings,'make_solids',True)), FieldSpec('remove_degenerate','Remove degenerate entities','bool',getattr(settings,'remove_degenerate',True)),
            FieldSpec('tolerance','Import tolerance','float',getattr(settings,'tolerance',1e-7),minimum=1e-12,maximum=1.0,decimals=10),
        ),parent,width=720)
    def values(self):
        values=super().values()
        if values['file'] and values['part_name']=='Part-1':values['part_name']=Path(values['file']).stem
        return values
    def accept(self):
        values=self.values(); path=Path(values['file']) if values['file'] else None
        if path is None or not path.exists():QMessageBox.warning(self,'Missing geometry','Choose an existing STEP, IGES or BREP file.'); return
        duplicate=values['part_name'].casefold() in self.existing_names and (self.active_part is None or values['part_name'].casefold()!=self.active_part.name.casefold())
        if duplicate:QMessageBox.warning(self,'Duplicate name',f"A part named '{values['part_name']}' already exists."); return
        super().accept()
