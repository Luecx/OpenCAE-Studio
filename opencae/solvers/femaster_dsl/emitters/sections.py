from __future__ import annotations

from ..command import command


def write_section(section, elset, orientation, writer, context):
    local_orientation = orientation if orientation not in (None, "", "Global") else None
    writers = {
        "Solid": _write_solid,
        "Truss": _write_truss,
        "Beam": _write_beam,
        "Shell": _write_shell,
    }
    callback = writers.get(section.section_type)
    if callback:
        callback(section, elset, local_orientation, writer)


def _write_solid(section, elset, orientation, writer):
    command(
        writer,
        "SOLIDSECTION",
        ELSET=elset,
        MATERIAL=section.material_name,
        ORIENTATION=orientation,
    )


def _write_truss(section, elset, orientation, writer):
    command(
        writer,
        "TRUSSSECTION",
        ELSET=elset,
        MATERIAL=section.material_name,
        AREA=section.area,
    )


def _write_beam(section, elset, orientation, writer):
    command(
        writer,
        "BEAMSECTION",
        [tuple(getattr(section, "direction", (0.0, 1.0, 0.0)))],
        ELSET=elset,
        MATERIAL=section.material_name,
        PROFILE=section.profile_name,
    )


def _write_shell(section, elset, orientation, writer):
    if section.shell_definition.startswith("ABD"):
        shear_row = tuple(value for row in section.shear_matrix for value in row)
        command(
            writer,
            "SHELLSECTION",
            [*section.abd_matrix, shear_row],
            ELSET=elset,
            TYPE="ABD",
            THICKNESS=section.thickness or None,
            ORIENTATION=orientation,
        )
        return
    command(
        writer,
        "SHELLSECTION",
        [(section.thickness,)],
        ELSET=elset,
        TYPE="INTEGRATED",
        MATERIAL=section.material_name,
        ORIENTATION=orientation,
    )
