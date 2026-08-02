from __future__ import annotations

from ..command import command


def write_profile(profile, writer, context):
    values = profile.properties()
    row = (
        values.get("Area", 0.0),
        values.get("Iyy", 0.0),
        values.get("Izz", 0.0),
        values.get("Torsion constant", 0.0),
        values.get("Iyz", 0.0),
        values.get("Centroid y", 0.0),
        values.get("Centroid z", 0.0),
    )
    command(writer, "PROFILE", [row], NAME=profile.name)
