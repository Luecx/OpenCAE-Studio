"""Writes FEMaster section definitions from current entity references."""

from __future__ import annotations

from ..command import command


def write_section(section, elset, orientation, writer, context):
    """Write one section assignment in FEMaster syntax."""
    local_orientation = (
        orientation if orientation not in (None, "", "Global") else None
    )
    callback = {
        "Solid": _write_solid,
        "Truss": _write_truss,
        "Beam": _write_beam,
        "Shell": _write_shell,
    }.get(section.section_type)
    if callback:
        callback(section, elset, local_orientation, writer, context)


def _required_name(ref, label, section, context):
    """Resolve one required section relationship to its solver name."""
    entity = context.resolve(ref) if ref else None
    if entity is None:
        raise ValueError(f"Section '{section.name}' has no valid {label}")
    return context.solver_name(entity, entity.name)


def _material(section, context):
    return _required_name(section.material_ref, "material", section, context)


def _profile(section, context):
    return _required_name(section.profile_ref, "profile", section, context)


def _write_solid(section, elset, orientation, writer, context):
    command(
        writer,
        "SOLIDSECTION",
        ELSET=elset,
        MATERIAL=_material(section, context),
        ORIENTATION=orientation,
    )


def _write_truss(section, elset, orientation, writer, context):
    command(
        writer,
        "TRUSSSECTION",
        ELSET=elset,
        MATERIAL=_material(section, context),
        AREA=section.area,
    )


def _write_beam(section, elset, orientation, writer, context):
    command(
        writer,
        "BEAMSECTION",
        [tuple(getattr(section, "direction", (0.0, 1.0, 0.0)))],
        ELSET=elset,
        MATERIAL=_material(section, context),
        PROFILE=_profile(section, context),
    )


def _write_shell(section, elset, orientation, writer, context):
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
        MATERIAL=_material(section, context),
        ORIENTATION=orientation,
    )
