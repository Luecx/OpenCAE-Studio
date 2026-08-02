from __future__ import annotations

from ..command import command


def write_field(field, writer, context):
    location = {"Nodal": "NODE", "Element": "ELEMENT", "Element-Nodal": "ELEMENT_NODAL"}.get(field.location, "NODE")
    data = [tuple(row) for row in field.table if row] if field.source_type == "Tabular" else []
    command(writer, "FIELD", data, NAME=context.solver_name(field, field.name), TYPE=location, COLS=field.components, FILL="NAN")
    if field.source_type != "Tabular": writer.comment(f"Field {field.name}: {field.source_type} source must be evaluated before solver export")
