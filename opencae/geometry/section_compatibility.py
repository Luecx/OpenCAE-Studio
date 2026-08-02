from .element_targets import resolve_target_ids


def incompatible_assignments(project, part, element_ids, family):
    if family not in {"Beam", "Truss"}:
        return []
    messages = []
    selected = set(element_ids)
    for assignment in part.section_assignments:
        region = project.try_resolve(assignment.region_ref)
        section = project.try_resolve(assignment.section_ref)
        if region is None or section is None:
            continue
        assigned = resolve_target_ids(part, [f"ElementSet:{region.name}"])
        if assigned & selected and section.section_type != family:
            messages.append(f"{assignment.name}: {section.name} is a {section.section_type} section")
    return messages
