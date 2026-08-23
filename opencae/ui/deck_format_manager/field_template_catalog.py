"""Define FEMaster Field, NORMAL and coordinate-system templates."""

from __future__ import annotations


def _field_spec(kind: str, row_fields, examples) -> dict:
    """Build one FIELD variant with explicit row-address and component values."""
    row = ", ".join("{row." + name + "}" for name, _description, _example in row_fields)
    return {
        "template": (
            f"*FIELD, NAME={{field_name}}, TYPE={kind}, "
            "COLS={component_count}, FILL={fill}\n"
            "{for row in rows}\n"
            f"{row}\n"
            "{endfor}"
        ),
        "fields": (
            ("field_name", "Field name", "FIELD-1"),
            ("component_count", "Number of values stored at each location", 2),
            ("fill", "Initial value mode: ZERO or NAN", "NAN"),
        ),
        "loops": (
            {
                "collection": "rows",
                "item": "row",
                "description": f"Rows for the {kind} Field domain.",
                "fields": row_fields,
                "examples": examples,
            },
        ),
        "commands": ("FIELD",),
    }


TEMPLATE_SPECS = {
    "fields.node": _field_spec(
        "NODE",
        (
            ("target", "Node identifier or qualified node reference", 101),
            ("values", "Field component values", "2.5, 3.5"),
        ),
        (
            {"target": 101, "values": "2.5, 3.5"},
            {"target": 102, "values": "4.5, 5.5"},
        ),
    ),
    "fields.element": _field_spec(
        "ELEMENT",
        (
            ("target", "Element identifier or qualified element reference", 42),
            ("values", "Field component values", "0.8"),
        ),
        ({"target": 42, "values": "0.8"}, {"target": 43, "values": "1.0"}),
    ),
    "fields.element_nodal": _field_spec(
        "ELEMENT_NODAL",
        (
            ("element", "Element identifier", 42),
            ("local_node", "Zero-based local node index", 0),
            ("values", "Field component values", "0.0, 0.0, 1.0"),
        ),
        (
            {"element": 42, "local_node": 0, "values": "0.0, 0.0, 1.0"},
            {"element": 42, "local_node": 1, "values": "0.0, 0.0, 1.0"},
        ),
    ),
    "fields.element_ip": _field_spec(
        "ELEMENT_IP",
        (
            ("element", "Element identifier", 42),
            ("local_ip", "Zero-based integration-point index", 0),
            ("values", "Field component values", "12.5"),
        ),
        ({"element": 42, "local_ip": 0, "values": "12.5"},),
    ),
    "fields.element_mp": _field_spec(
        "ELEMENT_MP",
        (
            ("element", "Element identifier", 42),
            ("local_ip", "Zero-based integration-point index", 0),
            ("local_mp", "Zero-based material-point index", 0),
            ("values", "Field component values", "0.15"),
        ),
        ({"element": 42, "local_ip": 0, "local_mp": 0, "values": "0.15"},),
    ),
    "fields.normal": {
        "template": "*NORMAL, FIELD={field_name}",
        "fields": (
            ("field_name", "Three-component ELEMENT_NODAL normal Field", "SHELL_NORMALS"),
        ),
        "loops": (),
        "commands": ("NORMAL",),
    },
    "coordinate_systems.rectangular": {
        "template": (
            "*ORIENTATION, NAME={name}, TYPE=RECTANGULAR\n"
            "{axis_1_x}, {axis_1_y}, {axis_1_z}, "
            "{axis_2_x}, {axis_2_y}, {axis_2_z}"
        ),
        "fields": (
            ("name", "Coordinate-system name", "LOCAL-1"),
            ("axis_1_x", "First direction X component", 1.0),
            ("axis_1_y", "First direction Y component", 0.0),
            ("axis_1_z", "First direction Z component", 0.0),
            ("axis_2_x", "Second direction X component", 0.0),
            ("axis_2_y", "Second direction Y component", 1.0),
            ("axis_2_z", "Second direction Z component", 0.0),
            ("axis_3_x", "Optional third direction X component", 0.0),
            ("axis_3_y", "Optional third direction Y component", 0.0),
            ("axis_3_z", "Optional third direction Z component", 1.0),
        ),
        "loops": (),
        "commands": ("ORIENTATION",),
    },
    "coordinate_systems.cylindrical": {
        "template": (
            "*ORIENTATION, NAME={name}, TYPE=CYLINDRICAL\n"
            "{base_x}, {base_y}, {base_z}, "
            "{radial_x}, {radial_y}, {radial_z}, "
            "{theta_x}, {theta_y}, {theta_z}"
        ),
        "fields": (
            ("name", "Coordinate-system name", "CYL-1"),
            ("base_x", "Cylindrical base point X", 0.0),
            ("base_y", "Cylindrical base point Y", 0.0),
            ("base_z", "Cylindrical base point Z", 0.0),
            ("radial_x", "Point defining the initial radial direction X", 1.0),
            ("radial_y", "Point defining the initial radial direction Y", 0.0),
            ("radial_z", "Point defining the initial radial direction Z", 0.0),
            ("theta_x", "Point defining the theta direction X", 0.0),
            ("theta_y", "Point defining the theta direction Y", 1.0),
            ("theta_z", "Point defining the theta direction Z", 0.0),
        ),
        "loops": (),
        "commands": ("ORIENTATION",),
    },
}
