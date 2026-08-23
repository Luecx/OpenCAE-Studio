"""Describe profile records exposed by the FEMaster deck-format editor."""

from __future__ import annotations


PROFILE_TYPES: tuple[tuple[str, str], ...] = (
    ("rectangle", "Rectangle"),
    ("box", "Box"),
    ("pipe", "Pipe"),
    ("circle", "Circle"),
    ("i", "I-Profile"),
    ("h", "H-Profile"),
    ("c", "C-Profile"),
    ("u", "U-Profile"),
    ("general", "General Profile"),
    ("graph", "Graph Profile"),
)

_PROFILE_FIELDS = (
    ("profile_name", "Solver profile name", "PROFILE-1"),
    ("area", "Cross-sectional area", 800.0),
    ("iyy", "Second moment of area Iyy", 26666.6666667),
    ("izz", "Second moment of area Izz", 106666.666667),
    ("torsion_constant", "Torsion constant J", 45000.0),
    ("iyz", "Product moment of area Iyz", 0.0),
    ("centroid_y", "Local centroid y-coordinate", 0.0),
    ("centroid_z", "Local centroid z-coordinate", 0.0),
)


def profile_tree_nodes() -> tuple[dict, ...]:
    """Return every profile type currently offered by OpenCAE."""
    return tuple(
        {"key": f"profiles.{key}", "label": label}
        for key, label in PROFILE_TYPES
    )


def profile_template_specs() -> dict[str, dict]:
    """Return FEMaster's common computed-property PROFILE record per profile type."""
    template = (
        "*PROFILE, NAME={profile_name}\n"
        "{area}, {iyy}, {izz}, {torsion_constant}, {iyz}, {centroid_y}, {centroid_z}"
    )
    return {
        f"profiles.{key}": {
            "template": template,
            "fields": _PROFILE_FIELDS,
            "loops": (),
        }
        for key, _label in PROFILE_TYPES
    }
