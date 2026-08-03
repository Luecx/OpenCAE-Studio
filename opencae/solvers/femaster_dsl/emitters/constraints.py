from __future__ import annotations

from opencae.model.entities.constraints import (
    DistributingCoupling, EquationConstraint, KinematicCoupling, MPCConstraint,
    RigidBodyConstraint, TieConstraint,
)
from opencae.model.selection import RegionProjection
from ..command import command
from .region_materialization import materialize_region


def write_constraint(value, writer, context):
    if isinstance(value, (KinematicCoupling, DistributingCoupling)):
        master = materialize_region(
            value.control_point,
            RegionProjection.SINGLE_CONTROL_NODE,
            writer,
            context,
            owner=value,
            proposed_name=f"__{value.name}_CONTROL",
            cache_key=("constraint-control", value.id),
            allowed_dimensions=(0,),
            min_count=1,
            max_count=1,
            require_unique_occurrence=True,
        ).name
        slave = materialize_region(
            value.slave,
            RegionProjection.NODES,
            writer,
            context,
            owner=value,
            proposed_name=f"__{value.name}_SLAVE",
            cache_key=("constraint-slave", value.id),
        ).name
        coupling_type = "KINEMATIC" if isinstance(value, KinematicCoupling) else "STRUCTURAL"
        command(writer, "COUPLING", [tuple(value.components)], MASTER=master, TYPE=coupling_type, SLAVE=slave)
        return

    if isinstance(value, TieConstraint):
        master = materialize_region(
            value.master,
            RegionProjection.FACETS,
            writer,
            context,
            owner=value,
            proposed_name=f"__{value.name}_MASTER",
            cache_key=("tie-master", value.id),
            allowed_dimensions=(2,),
        ).name
        slave = materialize_region(
            value.slave,
            RegionProjection.FACETS,
            writer,
            context,
            owner=value,
            proposed_name=f"__{value.name}_SLAVE",
            cache_key=("tie-slave", value.id),
            allowed_dimensions=(2,),
        ).name
        command(writer, "TIE", MASTER=master, SLAVE=slave, ADJUST=value.adjust, DISTANCE=value.distance)
        return

    if isinstance(value, RigidBodyConstraint):
        reference = materialize_region(
            value.reference,
            RegionProjection.SINGLE_CONTROL_NODE,
            writer,
            context,
            owner=value,
            proposed_name=f"__{value.name}_REFERENCE",
            cache_key=("rigid-reference", value.id),
            allowed_dimensions=(0,),
            min_count=1,
            max_count=1,
            require_unique_occurrence=True,
        ).name
        body = materialize_region(
            value.body,
            RegionProjection.ELEMENTS,
            writer,
            context,
            owner=value,
            proposed_name=f"__{value.name}_BODY",
            cache_key=("rigid-body", value.id),
        ).name
        command(writer, "RBM", ELSET=body, SET=reference)
        return

    if isinstance(value, (EquationConstraint, MPCConstraint)):
        writer.comment(f"Constraint {value.name} ({value.constraint_type}) has no documented FEMaster command mapping")
        return

    raise ValueError(f"Unsupported constraint class '{type(value).__name__}'")
