from __future__ import annotations

from ..command import command


_LOCATION_TYPES = {
    "Nodal": "NODE",
    "Element": "ELEMENT",
    "Element-Nodal": "ELEMENT_NODAL",
    "Integration Point": "ELEMENT_IP",
    "Material Point": "ELEMENT_MP",
    "Shell Normal": "ELEMENT_NODAL",
}


def write_field(field, writer, context):
    """Write generic FEMaster fields plus the NORMAL registration for shell normals."""
    location = _LOCATION_TYPES.get(field.location, "NODE")
    if field.location == "Shell Normal" and int(field.components) != 3:
        raise ValueError("Shell Normal fields require exactly three components")
    data = [tuple(row) for row in field.table if row] if field.source_type == "Tabular" else []
    name = context.solver_name(field, field.name)
    command(
        writer,
        "FIELD",
        data,
        NAME=name,
        TYPE=location,
        COLS=field.components,
        FILL="NAN",
    )
    if field.location == "Shell Normal":
        command(writer, "NORMAL", FIELD=name)
    if field.source_type != "Tabular":
        writer.comment(
            f"Field {field.name}: {field.source_type} source must be evaluated before solver export"
        )
