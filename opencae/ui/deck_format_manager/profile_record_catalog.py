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
    ("area", "Cross-sectional area A", 800.0),
    ("iy", "Second moment of area Iy", 26666.6666667),
    ("iz", "Second moment of area Iz", 106666.666667),
    ("jt", "Torsional constant Jt", 45000.0),
    ("iyz", "Product of inertia Iyz", 0.0),
    ("ey", "Section/shear-centre offset ey", 0.0),
    ("ez", "Section/shear-centre offset ez", 0.0),
    ("ref_y", "Beam reference-line offset ref_y", 0.0),
    ("ref_z", "Beam reference-line offset ref_z", 0.0),
)


def profile_tree_nodes() -> tuple[dict, ...]:
    """Return every profile type currently offered by OpenCAE."""
    return tuple(
        {
            "key": f"profiles.{key}",
            "label": label,
            "supported_formats": ("FEMaster",),
        }
        for key, label in PROFILE_TYPES
    )


def profile_template_specs() -> dict[str, dict]:
    """Return FEMaster's complete generic PROFILE record per OpenCAE profile type."""
    template = (
        "*PROFILE, NAME={profile_name}\n"
        "{area}, {iy}, {iz}, {jt}, {iyz}, {ey}, {ez}, {ref_y}, {ref_z}"
    )
    return {
        f"profiles.{key}": {
            "template": template,
            "fields": _PROFILE_FIELDS,
            "loops": (),
            "commands": ("PROFILE",),
        }
        for key, _label in PROFILE_TYPES
    }
