"""Emit typed spatial field definitions in FEMaster DSL form."""

from __future__ import annotations

from opencae.model.entities.fields import FieldLocation, FieldSourceKind

from ..command import command


_LOCATION_TYPES = {
    FieldLocation.NODAL: "NODE",
    FieldLocation.ELEMENT: "ELEMENT",
    FieldLocation.ELEMENT_NODAL: "ELEMENT_NODAL",
    FieldLocation.INTEGRATION_POINT: "ELEMENT_IP",
    FieldLocation.MATERIAL_POINT: "ELEMENT_MP",
    FieldLocation.SHELL_NORMAL: "ELEMENT_NODAL",
}


def write_field(field, writer, context):
    """Write generic FEMaster fields plus the NORMAL registration for shell normals."""
    location = _LOCATION_TYPES.get(field.location, "NODE")
    if field.location is FieldLocation.SHELL_NORMAL and int(field.components) != 3:
        raise ValueError("Shell Normal fields require exactly three components")
    data = (
        [tuple(row) for row in field.table if row]
        if field.source_type is FieldSourceKind.TABULAR
        else []
    )
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
    if field.location is FieldLocation.SHELL_NORMAL:
        command(writer, "NORMAL", FIELD=name)
    if field.source_type is not FieldSourceKind.TABULAR:
        writer.comment(
            f"Field {field.name}: {field.source_type} source must be evaluated before solver export"
        )
