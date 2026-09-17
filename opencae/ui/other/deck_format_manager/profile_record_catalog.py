"""Describe profile semantics and their native deck representations."""

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

_FEMASTER_FIELDS = (
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

_BEAM_FIELDS = (
    ("element_set", "Assigned beam element set", "BEAMS"),
    ("material_name", "Referenced material name", "STEEL"),
    ("orientation_x", "Beam n1 direction X", 0.0),
    ("orientation_y", "Beam n1 direction Y", 1.0),
    ("orientation_z", "Beam n1 direction Z", 0.0),
)

_DERIVED_FIELDS = (
    ("area", "Cross-sectional area A", 800.0),
    ("iyy", "Second moment Iyy", 26666.6666667),
    ("izz", "Second moment Izz", 106666.666667),
    ("iyz", "Product of inertia Iyz", 0.0),
    ("torsion_constant", "Torsional constant J", 45000.0),
)

_PROFILE_META = {
    "rectangle": {
        "formats": ("FEMaster", "Abaqus", "CalculiX"),
        "fields": (("width", "Rectangle width", 40.0), ("height", "Rectangle height", 20.0)),
        "abaqus": "*BEAM SECTION, ELSET={element_set}, MATERIAL={material_name}, SECTION=RECT\n{width}, {height}\n{orientation_x}, {orientation_y}, {orientation_z}",
        "calculix": "*BEAM SECTION, ELSET={element_set}, MATERIAL={material_name}, SECTION=RECT\n{width}, {height}\n{orientation_x}, {orientation_y}, {orientation_z}",
    },
    "box": {
        "formats": ("FEMaster", "Abaqus", "CalculiX"),
        "fields": (
            ("width", "Outer width", 40.0),
            ("height", "Outer height", 20.0),
            ("thickness", "Uniform wall thickness", 2.0),
        ),
        "abaqus": "*BEAM SECTION, ELSET={element_set}, MATERIAL={material_name}, SECTION=BOX\n{width}, {height}, {thickness}, {thickness}, {thickness}, {thickness}\n{orientation_x}, {orientation_y}, {orientation_z}",
        "calculix": "*BEAM SECTION, ELSET={element_set}, MATERIAL={material_name}, SECTION=BOX\n{width}, {height}, {thickness}, {thickness}, {thickness}, {thickness}\n{orientation_x}, {orientation_y}, {orientation_z}",
    },
    "pipe": {
        "formats": ("FEMaster", "Abaqus", "CalculiX"),
        "fields": (
            ("outer_radius", "Outer radius", 15.0),
            ("thickness", "Pipe wall thickness", 2.0),
        ),
        "abaqus": "*BEAM SECTION, ELSET={element_set}, MATERIAL={material_name}, SECTION=PIPE\n{outer_radius}, {thickness}\n{orientation_x}, {orientation_y}, {orientation_z}",
        "calculix": "*BEAM SECTION, ELSET={element_set}, MATERIAL={material_name}, SECTION=PIPE\n{outer_radius}, {thickness}\n{orientation_x}, {orientation_y}, {orientation_z}",
    },
    "circle": {
        "formats": ("FEMaster", "Abaqus", "CalculiX"),
        "fields": (("radius", "Circular section radius", 15.0),),
        "abaqus": "*BEAM SECTION, ELSET={element_set}, MATERIAL={material_name}, SECTION=CIRC\n{radius}\n{orientation_x}, {orientation_y}, {orientation_z}",
        "calculix": "*BEAM SECTION, ELSET={element_set}, MATERIAL={material_name}, SECTION=CIRC\n{radius}\n{orientation_x}, {orientation_y}, {orientation_z}",
    },
    "i": {
        "formats": ("FEMaster", "Abaqus"),
        "fields": (
            ("height", "Overall section height", 80.0),
            ("flange_width", "Flange width", 40.0),
            ("web_thickness", "Web thickness", 4.0),
            ("flange_thickness", "Flange thickness", 6.0),
        ),
        "abaqus": "*BEAM SECTION, ELSET={element_set}, MATERIAL={material_name}, SECTION=I\n{flange_width}, {flange_width}, {height}, {flange_thickness}, {flange_thickness}, {web_thickness}\n{orientation_x}, {orientation_y}, {orientation_z}",
    },
    "h": {
        "formats": ("FEMaster", "Abaqus"),
        "fields": (
            ("height", "Overall section height", 80.0),
            ("flange_width", "Flange width", 40.0),
            ("web_thickness", "Web thickness", 4.0),
            ("flange_thickness", "Flange thickness", 6.0),
        ),
        "abaqus": "*BEAM SECTION, ELSET={element_set}, MATERIAL={material_name}, SECTION=I\n{flange_width}, {flange_width}, {height}, {flange_thickness}, {flange_thickness}, {web_thickness}\n{orientation_x}, {orientation_y}, {orientation_z}",
    },
    "c": {
        "formats": ("FEMaster", "Abaqus", "CalculiX"),
        "fields": (
            ("height", "Overall section height", 80.0),
            ("flange_width", "Flange width", 40.0),
            ("web_thickness", "Web thickness", 4.0),
            ("flange_thickness", "Flange thickness", 6.0),
        ),
        "abaqus": "*BEAM SECTION, ELSET={element_set}, MATERIAL={material_name}, SECTION=CHANNEL\n{flange_width}, {flange_width}, {height}, {flange_thickness}, {flange_thickness}, {web_thickness}\n{orientation_x}, {orientation_y}, {orientation_z}",
        "calculix": "*BEAM SECTION, ELSET={element_set}, MATERIAL={material_name}, SECTION=BOX\n{flange_width}, {height}, {flange_thickness}, 0.0, {flange_thickness}, {web_thickness}\n{orientation_x}, {orientation_y}, {orientation_z}",
    },
    "u": {
        "formats": ("FEMaster", "Abaqus", "CalculiX"),
        "fields": (
            ("height", "Overall section height", 80.0),
            ("flange_width", "Flange width", 40.0),
            ("web_thickness", "Web thickness", 4.0),
            ("flange_thickness", "Flange thickness", 6.0),
        ),
        "abaqus": "*BEAM SECTION, ELSET={element_set}, MATERIAL={material_name}, SECTION=CHANNEL\n{flange_width}, {flange_width}, {height}, {flange_thickness}, {flange_thickness}, {web_thickness}\n{orientation_x}, {orientation_y}, {orientation_z}",
        "calculix": "*BEAM SECTION, ELSET={element_set}, MATERIAL={material_name}, SECTION=BOX\n{flange_width}, {height}, {flange_thickness}, 0.0, {flange_thickness}, {web_thickness}\n{orientation_x}, {orientation_y}, {orientation_z}",
    },
    "general": {
        "formats": ("FEMaster", "Abaqus"),
        "fields": _DERIVED_FIELDS,
        "abaqus": "*BEAM GENERAL SECTION, ELSET={element_set}, SECTION=GENERAL\n{area}, {iyy}, {iyz}, {izz}, {torsion_constant}\n{orientation_x}, {orientation_y}, {orientation_z}",
    },
    "graph": {
        "formats": ("FEMaster", "Abaqus"),
        "fields": _DERIVED_FIELDS,
        "abaqus": "*BEAM GENERAL SECTION, ELSET={element_set}, SECTION=GENERAL\n{area}, {iyy}, {iyz}, {izz}, {torsion_constant}\n{orientation_x}, {orientation_y}, {orientation_z}",
    },
}


def profile_tree_nodes() -> tuple[dict, ...]:
    """Return every OpenCAE profile with only genuinely compatible dialects enabled."""
    return tuple(
        {
            "key": f"profiles.{key}",
            "label": label,
            "supported_formats": tuple(_PROFILE_META[key]["formats"]),
        }
        for key, label in PROFILE_TYPES
    )


def profile_template_specs() -> dict[str, dict]:
    """Return standalone FEMaster and embedded Abaqus/CalculiX beam-section forms."""
    femaster_template = (
        "*PROFILE, NAME={profile_name}\n"
        "{area}, {iy}, {iz}, {jt}, {iyz}, {ey}, {ez}, {ref_y}, {ref_z}"
    )
    result: dict[str, dict] = {}
    for key, _label in PROFILE_TYPES:
        meta = _PROFILE_META[key]
        variants: dict[str, dict] = {}
        native_fields = _BEAM_FIELDS + tuple(meta["fields"])
        if "abaqus" in meta:
            variants["Abaqus"] = {
                "template": meta["abaqus"],
                "fields": native_fields,
                "commands": ("BEAM SECTION", "BEAM GENERAL SECTION"),
            }
        if "calculix" in meta:
            variants["CalculiX"] = {
                "template": meta["calculix"],
                "fields": native_fields,
                "commands": ("BEAM SECTION",),
            }
        result[f"profiles.{key}"] = {
            "template": femaster_template,
            "fields": _FEMASTER_FIELDS,
            "loops": (),
            "commands": ("PROFILE",),
            "formats": variants,
        }
    return result


__all__ = ["PROFILE_TYPES", "profile_template_specs", "profile_tree_nodes"]
