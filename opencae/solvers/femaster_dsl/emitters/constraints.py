from opencae.model.entities.constraints import ConstraintReferenceKind, ConstraintType
from ..command import command
from .target_resolution import entity_target_name


def write_constraint(value, writer, context):
    master_entity = context.resolve(value.master_ref)
    slave_entity = context.resolve(value.slave_ref)
    if master_entity is None:
        raise ValueError(f"Constraint '{value.name}' has no valid master")
    if slave_entity is None:
        raise ValueError(f"Constraint '{value.name}' has no valid slave")
    master = entity_target_name(master_entity, value.master.kind.value, writer, context)
    slave = entity_target_name(slave_entity, value.slave.kind.value, writer, context)
    kind = ConstraintType.coerce(value.constraint_type)
    if kind in {ConstraintType.KINEMATIC, ConstraintType.DISTRIBUTING}:
        options = {"MASTER": master, "TYPE": "KINEMATIC" if kind == ConstraintType.KINEMATIC else "STRUCTURAL"}
        options["SFSET" if value.slave.kind == ConstraintReferenceKind.SURFACE else "SLAVE"] = slave
        command(writer, "COUPLING", [value.components], **options)
    elif kind == ConstraintType.TIE:
        command(writer, "TIE", MASTER=master, SLAVE=slave, ADJUST=value.adjust, DISTANCE=value.distance)
    elif kind == ConstraintType.RIGID_BODY:
        command(writer, "RBM", ELSET=slave or master)
    else:
        writer.comment(f"Constraint {value.name} ({kind}) has no documented FEMaster command mapping")
