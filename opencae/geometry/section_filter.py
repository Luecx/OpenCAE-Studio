from opencae.model.element_catalog import CATALOG
from opencae.model.entities.mesh import ElementTopology
from opencae.model.core import RegionMemberKind, RegionMemberRef
from .element_records import records
from .element_targets import resolve_target_ids


def region_families(part,region):
    ids=resolve_target_ids(part,[f"ElementSet:{region.name}"]);elements=records(part.mesh);families={_family(elements[eid]) for eid in ids if eid in elements}
    if families:return families
    inferred=set()
    for member in region.members:
        if isinstance(member, RegionMemberRef):
            if member.kind == RegionMemberKind.CELL: inferred.add("Solid")
            elif member.kind == RegionMemberKind.FACE: inferred.add("Shell")
            continue
        label=str(member).split(".")[-1]
        if label.startswith("Cell-"):inferred.add("Solid")
        elif label.startswith("Face-"):inferred.add("Shell")
    return inferred


def compatible_sections(project,part,region_id):
    region=project.try_resolve(region_id) if region_id else None
    if region is None:return list(project.sections)
    families=region_families(part,region);return [item for item in project.sections if not families or item.section_type in families]


def compatible_section_names(project,part,region_name):
    region=next((item for item in part.element_sets if item.name==region_name),None)
    return [item.name for item in compatible_sections(project,part,region.id if region else None)]


def _family(element):
    if element.topology==ElementTopology.LINE:return "Beam" if element.formulation=="Beam" else "Truss"
    return "Shell" if CATALOG[element.topology].dimension==2 else "Solid"
