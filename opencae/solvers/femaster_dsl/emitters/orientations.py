from __future__ import annotations

from ..command import command


def write_orientation(system, writer, context):
    kind = (
        "CYLINDRICAL"
        if str(system.system_type).lower().startswith("cyl")
        else "RECTANGULAR"
    )
    command(
        writer,
        "ORIENTATION",
        [(*system.origin, *system.axis_1, *system.axis_2)],
        NAME=system.name,
        TYPE=kind,
    )
