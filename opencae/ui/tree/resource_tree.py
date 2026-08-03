from .tree_items import ensure_expandable, folder, item


def append_materials(root, materials):
    group = folder("Materials", "materials", count=len(materials)); root.appendRow(group)
    categories = ("Elasticity", "Density", "Plasticity", "Thermal expansion")
    for material in materials:
        node = item(material.name, material, "material"); group.appendRow(node)
        assigned = {behavior.category: behavior.behavior_type for behavior in material.behaviors}
        for category in categories: node.appendRow(item(f"{category}: {assigned.get(category, '-')}", None, "info"))
    return ensure_expandable(group, materials, "No materials")


def append_profiles(root, profiles):
    group = folder("Profiles", "profiles", count=len(profiles)); root.appendRow(group)
    for profile in profiles:
        node = item(profile.name, profile, "profile"); group.appendRow(node)
        node.appendRow(item(profile.profile_type, None, "info"))
        for key, value in profile.dimensions.items(): node.appendRow(item(f"{key}: {value}", None, "info"))
    return ensure_expandable(group, profiles, "No profiles")


def append_sections(root, sections, project=None):
    group = folder("Sections", "sections", count=len(sections)); root.appendRow(group)
    for section in sections:
        node = item(section.name, section, "section"); group.appendRow(node)
        node.appendRow(item(section.section_type, None, "info"))
        material = project.try_resolve(section.material_ref) if project and section.material_ref else None
        profile = project.try_resolve(section.profile_ref) if project and section.profile_ref else None
        if material: node.appendRow(item(f"Material: {material.name}", None, "info"))
        if profile: node.appendRow(item(f"Profile: {profile.name}", None, "info"))
    return ensure_expandable(group, sections, "No sections")


def append_fields(root, fields):
    group = folder("Fields", "fields", count=len(fields)); root.appendRow(group)
    for value in fields:
        label = f"{value.name}  [{value.location}, {value.components} column(s)]"
        group.appendRow(item(label, value, "field_definition"))
    return ensure_expandable(group, fields, "No fields")
