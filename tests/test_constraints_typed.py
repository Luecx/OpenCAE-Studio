from pathlib import Path
from tempfile import TemporaryDirectory
from opencae.model.core import EntityRef
from opencae.model.entities.constraints import ConstraintReference,ConstraintReferenceKind,create_constraint
from opencae.persistence.project_io import load_project,save_project
from opencae.solvers.femaster import FEMasterAdapter
from tests.test_femaster_dsl import _project


def test_constraint_references_survive_roundtrip():
    project=_project(); from opencae.model.entities.regions.reference_point import ReferencePoint
    point=ReferencePoint(name="RP",position=(0,0,0),scope="Assembly"); project.assembly.reference_points.append(point)
    project.assembly.constraints.append(create_constraint("Kinematic Coupling",name="C",master=ConstraintReference(ConstraintReferenceKind.REFERENCE_POINT, EntityRef.of(point)),slave=ConstraintReference(ConstraintReferenceKind.NODE_SET, EntityRef(legacy_name="FACE_NODES"))))
    with TemporaryDirectory() as directory:
        path=Path(directory)/"model.ocae"; save_project(project,path); loaded=load_project(path)
    value=loaded.assembly.constraints[0]; assert loaded.resolve(value.master.ref).name=="RP"; assert value.slave.kind==ConstraintReferenceKind.NODE_SET


def test_reference_point_is_exported_through_individual_nset():
    project=_project(); from opencae.model.entities.regions.reference_point import ReferencePoint
    project.assembly.reference_points.append(ReferencePoint(name="CONTROL",position=(0,0,0),scope="Assembly"))
    project.assembly.constraints.append(create_constraint("Kinematic Coupling",name="C",master=ConstraintReference(ConstraintReferenceKind.REFERENCE_POINT, EntityRef(legacy_name="CONTROL")),slave=ConstraintReference(ConstraintReferenceKind.NODE_SET, EntityRef(legacy_name="FACE_NODES"))))
    deck=FEMasterAdapter().write_deck_text(project,project.analyses[0])
    assert "*NSET, NSET=ASSEMBLY_RP_CONTROL\n5" in deck
    assert "*COUPLING, MASTER=ASSEMBLY_RP_CONTROL, TYPE=KINEMATIC, SLAVE=FACE_NODES" in deck
