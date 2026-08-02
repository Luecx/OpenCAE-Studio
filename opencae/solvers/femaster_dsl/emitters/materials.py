from __future__ import annotations

from ..command import command


def write_material(material, writer, context):
    command(writer, "MATERIAL", NAME=material.name)
    for behavior in material.behaviors:
        _write_behavior(material.name, behavior, writer)


def _write_behavior(material_name, behavior, writer):
    kind = type(behavior).__name__
    if kind == "IsotropicElasticity":
        command(
            writer,
            "ELASTIC",
            [(behavior.youngs_modulus, behavior.poisson_ratio)],
            TYPE="ISOTROPIC",
        )
    elif kind == "NeoHookeElasticity":
        command(
            writer,
            "HYPERELASTIC",
            [(behavior.c10, behavior.d1)],
            flags=("NEO HOOKE",),
        )
    elif kind == "DensityBehavior":
        command(writer, "DENSITY", [(behavior.value,)])
    elif kind == "IsotropicThermalExpansion":
        command(writer, "THERMALEXPANSION", [(behavior.coefficient,)])
    elif kind == "IsotropicPlasticity":
        writer.comment(
            f"Material {material_name}: plasticity is not a documented FEMaster material command"
        )
