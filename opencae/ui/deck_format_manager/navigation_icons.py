"""Maps deck-format record families onto the existing OpenCAE icon language."""

from opencae.ui.core.icon_factory import IconKind


def deck_record_icon_kind(key: str) -> IconKind:
    """Return the semantic OpenCAE icon kind for one editor record key."""
    root = key.split(".", 1)[0]
    return {
        "general": IconKind.SETTINGS,
        "mesh": IconKind.MESH,
        "node_sets": IconKind.NODE_SET,
        "element_sets": IconKind.ELEMENT_SET,
        "surfaces": IconKind.SURFACE,
        "materials": IconKind.MATERIAL,
        "sections": IconKind.SECTION,
        "profiles": IconKind.PROFILE,
        "fields": IconKind.FIELD,
        "coordinate_systems": IconKind.CSYS,
        "reference_points": IconKind.RP,
        "constraints": IconKind.CONSTRAINT,
        "boundary_conditions": IconKind.SUPPORT,
        "loads": IconKind.LOAD,
        "analysis": IconKind.ANALYSIS,
    }.get(root, IconKind.DECK)
