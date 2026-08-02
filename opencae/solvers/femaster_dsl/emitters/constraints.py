from opencae.model.entities.constraints import ConstraintReferenceKind, ConstraintType
from ..command import command


def write_constraint(value, writer, context):
    aliases = context.options.get("region_aliases", {})
    master = aliases.get(value.master.name, value.master.name)
    slave = aliases.get(value.slave.name, value.slave.name)
    kind = ConstraintType.coerce(value.constraint_type)
    if kind in {ConstraintType.KINEMATIC, ConstraintType.DISTRIBUTING}:
        options = {"MASTER": master, "TYPE": "KINEMATIC" if kind == ConstraintType.KINEMATIC else "STRUCTURAL"}
        options["SFSET" if value.slave.kind == ConstraintReferenceKind.SURFACE else "SLAVE"] = slave
        flags = value.parameters.get("components", (1, 1, 1, 1, 1, 1)); command(writer, "COUPLING", [flags], **options)
    elif kind == ConstraintType.TIE:
        command(writer, "TIE", MASTER=master, SLAVE=slave, ADJUST=value.parameters.get("adjust"), DISTANCE=value.parameters.get("distance"))
    elif kind == ConstraintType.RIGID_BODY:
        command(writer, "RBM", ELSET=slave or master)
    else:
        writer.comment(f"Constraint {value.name} ({kind}) has no documented FEMaster command mapping")
