from PyQt6.QtWidgets import QMessageBox

from opencae.model.core import EntityRef
from opencae.model.naming import is_unique
from opencae.ui.core.fields import FieldSpec
from opencae.ui.core.form_dialog import FormDialog


class SectionAssignmentDialog(FormDialog):
    def __init__(self,sections=(),regions=(),orientations=(),create_section=None,create_region=None,pick_region=None,default_name="Section Assignment-1",existing_names=(),assignment=None,section_filter=None,parent=None):
        self.assignment=assignment; self.existing_names=tuple(existing_names); self.section_filter=section_filter
        super().__init__("Edit Section Assignment" if assignment else "Assign Section",(
            FieldSpec("name","Name","text",getattr(assignment,"name",default_name)),
            FieldSpec("section_id","Section","reference",assignment.section_ref.entity_id if assignment else (sections[0].id if sections else ""),tuple(sections),create_callback=create_section),
            FieldSpec("region_id","Region","reference",assignment.region_ref.entity_id if assignment else (regions[0].id if regions else ""),tuple(regions),create_callback=create_region,pick_callback=pick_region),
            FieldSpec("orientation_id","Orientation","reference",assignment.orientation_ref.entity_id if assignment and assignment.orientation_ref else None,(("Global",None),*orientations)),
        ),parent,width=560,allow_apply=True)
        if section_filter:
            region_editor=self._editors["region_id"]; region_editor.value_changed.connect(self._filter_sections); self._filter_sections(region_editor.currentValue())

    def _filter_sections(self,region_id):
        editor=self._editors["section_id"]; values=tuple(self.section_filter(region_id)); editor.set_values(values)

    def values(self):
        values=super().values(); section_id=values.pop("section_id"); region_id=values.pop("region_id"); orientation_id=values.pop("orientation_id")
        values.update(section_ref=EntityRef(str(section_id),"Section") if section_id else EntityRef(expected_type="Section"),region_ref=EntityRef(str(region_id),"ElementSet") if region_id else EntityRef(expected_type="ElementSet"),orientation_ref=EntityRef(str(orientation_id),"Orientation") if orientation_id else None)
        return values

    def validate(self):
        raw=super().values(); current_name=self.assignment.name if self.assignment else None
        if not is_unique(raw["name"],self.existing_names,current_name):QMessageBox.warning(self,"Duplicate name",f"A section assignment named '{raw['name']}' already exists.");return False
        if not raw["section_id"]:QMessageBox.warning(self,"Missing section","Create or select a section.");return False
        if not raw["region_id"]:QMessageBox.warning(self,"Missing region","Create or select a region.");return False
        if self.section_filter and raw["section_id"] not in {item.id for item in self.section_filter(raw["region_id"])}:QMessageBox.warning(self,"Incompatible section","The selected section is not compatible with the element families in this region.");return False
        return True
