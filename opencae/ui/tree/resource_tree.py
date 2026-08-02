from .tree_items import ensure_expandable, folder, item


def append_materials(root, materials):
    group = folder("Materials", "materials"); root.appendRow(group)
    categories = ("Elasticity", "Density", "Plasticity", "Thermal expansion")
    for material in materials:
        node = item(material.name, material, "material"); group.appendRow(node)
        assigned = {behavior.category: behavior.behavior_type for behavior in material.behaviors}
        for category in categories: node.appendRow(item(f"{category}: {assigned.get(category, '-')}", None, "info"))
    return ensure_expandable(group, materials, "No materials")


def append_profiles(root, profiles):
    group = folder("Profiles", "profiles"); root.appendRow(group)
    for profile in profiles:
        node = item(profile.name, profile, "profile"); group.appendRow(node)
        node.appendRow(item(profile.profile_type, None, "info"))
        for key, value in profile.dimensions.items(): node.appendRow(item(f"{key}: {value}", None, "info"))
    return ensure_expandable(group, profiles, "No profiles")


def append_sections(root, sections):
    group = folder("Sections", "sections"); root.appendRow(group)
    for section in sections:
        node = item(section.name, section, "section"); group.appendRow(node)
        node.appendRow(item(section.section_type, None, "info"))
        if getattr(section, "material_name", ""): node.appendRow(item(f"Material: {section.material_name}", None, "info"))
        if getattr(section, "profile_name", ""): node.appendRow(item(f"Profile: {section.profile_name}", None, "info"))
    return ensure_expandable(group, sections, "No sections")


def append_fields(root, fields):
    group = folder("Fields", "fields"); root.appendRow(group)
    for value in fields:
        label = f"{value.name}  [{value.location}, {value.components} column(s)]"
        group.appendRow(item(label, value, "field_definition"))
    return ensure_expandable(group, fields, "No fields")
