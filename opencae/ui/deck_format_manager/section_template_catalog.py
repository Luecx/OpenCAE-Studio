"""Define FEMaster section-assignment templates, including the full ABD form."""

from __future__ import annotations


def _abd_fields() -> tuple[tuple[str, str, float], ...]:
    """Return all 36 generalized plus four transverse-shear stiffness fields."""
    generalized = tuple(
        (
            f"k{row}{column}",
            f"Generalized 6x6 stiffness entry K{row}{column}",
            1.0 if row == column else 0.0,
        )
        for row in range(1, 7)
        for column in range(1, 7)
    )
    shear = tuple(
        (
            f"s{row}{column}",
            f"Transverse-shear 2x2 stiffness entry S{row}{column}",
            1.0 if row == column else 0.0,
        )
        for row in range(1, 3)
        for column in range(1, 3)
    )
    return generalized + shear


def _abd_data_template() -> str:
    """Return the documented row-major 36+4-value ABD data block."""
    rows = [
        ", ".join(f"{{k{row}{column}}}" for column in range(1, 7))
        for row in range(1, 7)
    ]
    rows.extend(
        ", ".join(f"{{s{row}{column}}}" for column in range(1, 3))
        for row in range(1, 3)
    )
    return "\n".join(rows)


TEMPLATE_SPECS = {
    "sections.solid": {
        "template": "*SOLID SECTION, ELSET={element_set}, MATERIAL={material_name}",
        "fields": (
            ("element_set", "Assigned solid element set", "SOLID"),
            ("material_name", "Referenced material name", "STEEL"),
            ("orientation", "Optional material orientation name", "MAT_AXES"),
        ),
        "loops": (),
        "commands": ("SOLID SECTION",),
    },
    "sections.shell.integrated": {
        "template": (
            "*SHELL SECTION, ELSET={element_set}, MATERIAL={material_name}, "
            "TYPE=INTEGRATED\n{thickness}"
        ),
        "fields": (
            ("element_set", "Assigned shell element set", "SKIN"),
            ("material_name", "Referenced material name", "ALUMINIUM"),
            ("thickness", "Physical shell thickness", 2.0),
            ("orientation", "Optional section/material orientation", "MAT_AXES"),
            ("csys_axis", "Coordinate-system axis used in the shell plane", 1),
            ("nominal_thickness", "Optional THICKNESS keyword parameter", 2.0),
        ),
        "loops": (),
        "commands": ("SHELL SECTION",),
    },
    "sections.shell.abd": {
        "template": (
            "*SHELL SECTION, ELSET={element_set}, TYPE=ABD\n" + _abd_data_template()
        ),
        "fields": (
            ("element_set", "Assigned shell element set", "LAMINATE"),
            ("material_name", "Optional material reference", "LAMINA"),
            ("orientation", "Optional shell orientation name", "LAMINATE_AXES"),
            ("csys_axis", "Coordinate-system axis used in the shell plane", 1),
        )
        + _abd_fields(),
        "loops": (),
        "commands": ("SHELL SECTION",),
    },
    "sections.beam": {
        "template": (
            "*BEAM SECTION, ELSET={element_set}, MATERIAL={material_name}, "
            "PROFILE={profile_name}\n{orientation_x}, {orientation_y}, {orientation_z}"
        ),
        "fields": (
            ("element_set", "Assigned beam element set", "BEAMS"),
            ("material_name", "Referenced material name", "STEEL"),
            ("profile_name", "Referenced FEMaster profile name", "BEAM_PROFILE"),
            ("orientation_x", "Section direction X component", 0.0),
            ("orientation_y", "Section direction Y component", 1.0),
            ("orientation_z", "Section direction Z component", 0.0),
        ),
        "loops": (),
        "commands": ("BEAM SECTION",),
    },
    "sections.truss": {
        "template": (
            "*TRUSS SECTION, ELSET={element_set}, MATERIAL={material_name}\n{area}"
        ),
        "fields": (
            ("element_set", "Assigned truss element set", "BARS"),
            ("material_name", "Referenced material name", "STEEL"),
            ("area", "Positive truss cross-sectional area", 100.0),
        ),
        "loops": (),
        "commands": ("TRUSS SECTION",),
    },
}
