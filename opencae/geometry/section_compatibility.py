from opencae.model.selection import RegionProjection, RegionRequirement, RegionResolver


def incompatible_assignments(project, part, element_ids, family):
    if family not in {"Beam", "Truss"}: return []
    messages = []; selected = set(element_ids); resolver = RegionResolver(project)
    for assignment in part.section_assignments:
        section = project.try_resolve(assignment.section_ref)
        if section is None: continue
        resolved = resolver.resolve(assignment.target, RegionRequirement(RegionProjection.ELEMENTS, (0,1,2,3), 0))
        assigned = {item.element_id for item in resolved.elements if item.owner_id == part.id}
        if assigned & selected and section.section_type != family:
            messages.append(f"{assignment.name}: {section.name} is a {section.section_type} section")
    return messages
