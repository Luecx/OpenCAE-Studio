from PyQt6.QtWidgets import QDialog, QMessageBox

from opencae.model.resources import Material, create_profile, create_section
from opencae.model.naming import next_name
from opencae.model.entities.fields import FieldDefinition
from opencae.ui.dialogs.field_definition import FieldDefinitionDialog
from opencae.ui.dialogs.material import MaterialDialog
from opencae.ui.dialogs.material_property import MaterialPropertyDialog
from opencae.ui.dialogs.profile import ProfileDialog
from opencae.ui.dialogs.section import SectionDialog


class ResourceController:
    def __init__(self, store, parent): self.store=store; self.parent=parent
    def material(self): return self._material_dialog()
    def profile(self, kind=None): return self._profile_dialog(initial_type=kind)
    def section(self, kind=None): return self._section_dialog(initial_type=kind)
    def field(self): return self._field_dialog()

    def selected_material(self):
        selected=self.store.selection
        if isinstance(selected,Material): return selected
        return self.store.project.materials[-1] if self.store.project.materials else None

    def set_behavior(self, category):
        material=self.selected_material()
        if material is None:
            QMessageBox.information(self.parent,"No material","Create or select a material first."); return
        current=next((item for item in material.behaviors if item.category==category),None)
        dialog=MaterialPropertyDialog(current,self.parent,category)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        behavior=dialog.behavior_value()
        def apply(_project):
            material.behaviors=[item for item in material.behaviors if item.category!=category]; material.behaviors.append(behavior)
        self.store.mutate(f"Set {category} for {material.name}",apply)

    def _material_dialog(self, material=None, parent=None):
        project=self.store.project; dialog=MaterialDialog(material,[item.name for item in project.materials],parent or self.parent,next_name("Material",project.materials))
        if dialog.exec()!=QDialog.DialogCode.Accepted:return None
        value=Material(**dialog.values()); self._replace_or_append(project.materials,material,value,f"{'Edited' if material else 'Created'} material {value.name}",'material')
        self.store.select(value); return value.name

    def _profile_dialog(self, profile=None, initial_type=None, parent=None):
        project=self.store.project; dialog=ProfileDialog(profile,[item.name for item in project.profiles],parent or self.parent,initial_type,next_name("Profile",project.profiles))
        if dialog.exec()!=QDialog.DialogCode.Accepted:return None
        values=dialog.values(); kind=values.pop('profile_type'); value=create_profile(kind,**values)
        self._replace_or_append(project.profiles,profile,value,f"{'Edited' if profile else 'Created'} profile {value.name}",'profile')
        self.store.select(value); return value.name

    def _section_dialog(self, section=None, initial_type=None, parent=None):
        project=self.store.project; owner=parent or self.parent
        create_material=lambda child=None: self._material_dialog(parent=child or owner)
        create_profile=lambda child=None: self._profile_dialog(parent=child or owner)
        dialog=SectionDialog([item.name for item in project.materials],[item.name for item in project.profiles],create_material,create_profile,section,[item.name for item in project.sections],owner,initial_type,next_name("Section",project.sections))
        if dialog.exec()!=QDialog.DialogCode.Accepted:return None
        values=dialog.values(); kind=values.pop('section_type'); value=create_section(kind,**values)
        self._replace_or_append(project.sections,section,value,f"{'Edited' if section else 'Created'} section {value.name}",'section')
        self.store.select(value); return value.name

    def _field_dialog(self, field=None, parent=None):
        project=self.store.project; regions=[]
        for part in project.parts: regions.extend(f"{part.name}.{item.name}" for item in (*part.node_sets,*part.element_sets))
        dialog=FieldDefinitionDialog(field,[item.name for item in project.fields],regions,parent or self.parent,next_name("Field",project.fields))
        if dialog.exec()!=QDialog.DialogCode.Accepted:return None
        value=FieldDefinition(**dialog.values()); self._replace_or_append(project.fields,field,value,f"{'Edited' if field else 'Created'} field {value.name}",'field')
        return value.name

    def edit(self, entity):
        if isinstance(entity,Material): return self._material_dialog(entity)
        from opencae.model.entities.profiles import Profile
        from opencae.model.entities.sections import Section
        if isinstance(entity,Profile): return self._profile_dialog(entity)
        if isinstance(entity,Section): return self._section_dialog(entity)
        if isinstance(entity,FieldDefinition): return self._field_dialog(entity)

    def _replace_or_append(self,collection,old,new,description,kind):
        def apply(project):
            if old is None: collection.append(new); return
            old_name=old.name; collection[collection.index(old)]=new
            if old_name==new.name:return
            if kind=='material':
                for section in project.sections:
                    if section.material_name==old_name:section.material_name=new.name
            elif kind=='profile':
                for section in project.sections:
                    if getattr(section,'profile_name','')==old_name:section.profile_name=new.name
            elif kind=='section':
                for part in project.parts:
                    for assignment in part.section_assignments:
                        if assignment.section_name==old_name:assignment.section_name=new.name
        self.store.mutate(description,apply)
