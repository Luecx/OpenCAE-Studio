from opencae.model.loads import create_load, create_support
from opencae.model.resources import create_profile, create_section


def legacy_load(data):
    data = dict(data)
    return create_load(data.pop("load_type", "Load"), **data)


def legacy_support(data):
    data = dict(data)
    return create_support(data.pop("support_type", "Support"), **data)


def legacy_profile(data):
    data = dict(data)
    return create_profile(data.pop("profile_type", "General"), **data)


def legacy_section(data):
    data = dict(data)
    return create_section(data.pop("section_type", "Section"), **data)
