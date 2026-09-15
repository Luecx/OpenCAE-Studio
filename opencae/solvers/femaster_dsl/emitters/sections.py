"""Writes FEMaster section definitions from current entity references."""

from __future__ import annotations

import numpy as np

from ..command import command


def write_section(section, elset, orientation, writer, context, instance=None):
    """Write one section assignment in FEMaster syntax."""
    local_orientation = (
        orientation if orientation not in (None, "", "Global") else None
    )
    if section.section_type == "Beam":
        _write_beam(section, elset, local_orientation, writer, context, instance)
        return
    callback = {
        "Solid": _write_solid,
        "Truss": _write_truss,
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


def _write_beam(section, elset, orientation, writer, context, instance=None):
    n1 = np.asarray(section.n1, dtype=float)
    if instance is not None:
        n1 = _instance_rotation(instance) @ n1
    command(
        writer,
        "BEAMSECTION",
        [tuple(float(value) for value in n1)],
        ELSET=elset,
        MATERIAL=_material(section, context),
        PROFILE=_profile(section, context),
    )


def _instance_rotation(instance) -> np.ndarray:
    """Return the same XYZ instance rotation used for exported mesh nodes."""
    angles = np.radians(np.asarray(instance.rotation, dtype=float))
    cx, cy, cz = np.cos(angles)
    sx, sy, sz = np.sin(angles)
    rx = np.asarray(((1, 0, 0), (0, cx, -sx), (0, sx, cx)), dtype=float)
    ry = np.asarray(((cy, 0, sy), (0, 1, 0), (-sy, 0, cy)), dtype=float)
    rz = np.asarray(((cz, -sz, 0), (sz, cz, 0), (0, 0, 1)), dtype=float)
    return rz @ ry @ rx


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
