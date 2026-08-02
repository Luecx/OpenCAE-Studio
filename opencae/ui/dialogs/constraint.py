from PyQt6.QtWidgets import QMessageBox

from opencae.model.core import EntityRef
from opencae.model.entities.constraints import ConstraintReference, ConstraintReferenceKind, ConstraintType
from opencae.model.naming import is_unique
from opencae.ui.core.fields import FieldSpec
from opencae.ui.core.form_dialog import FormDialog


class ConstraintDialog(FormDialog):
    def __init__(self, masters=(), slaves=(), create_master=None, create_slave=None, parent=None,
                 default_name="Constraint-1", existing_names=(), initial_type=ConstraintType.KINEMATIC,
                 constraint=None, pick_master=None, pick_slave=None):
        self.existing_names = tuple(existing_names)
        self.constraint = constraint
        self.master_refs = _reference_map(masters, ConstraintReferenceKind.REFERENCE_POINT)
        self.slave_refs = _reference_map(slaves, ConstraintReferenceKind.UNKNOWN)
        current_master = getattr(getattr(constraint, "master", None), "ref", EntityRef()).entity_id
        current_slave = getattr(getattr(constraint, "slave", None), "ref", EntityRef()).entity_id
        components = tuple(getattr(constraint, "components", (1, 1, 1, 1, 1, 1)))
        super().__init__("Edit Constraint" if constraint else "Create Constraint", (
            FieldSpec("name", "Name", "text", getattr(constraint, "name", default_name)),
            FieldSpec("constraint_type", "Type", "choice", str(getattr(constraint, "constraint_type", initial_type)), tuple(item.value for item in ConstraintType)),
            FieldSpec("master_id", "Master / control", "reference", current_master or _first(self.master_refs), tuple((item[0], key) for key, item in self.master_refs.items()), create_callback=create_master, pick_callback=pick_master),
            FieldSpec("slave_id", "Slave / region", "reference", current_slave or _first(self.slave_refs), tuple((item[0], key) for key, item in self.slave_refs.items()), create_callback=create_slave, pick_callback=pick_slave),
            FieldSpec("u1", "U1", "bool", bool(components[0])),
            FieldSpec("u2", "U2", "bool", bool(components[1])),
            FieldSpec("u3", "U3", "bool", bool(components[2])),
            FieldSpec("r1", "R1", "bool", bool(components[3])),
            FieldSpec("r2", "R2", "bool", bool(components[4])),
            FieldSpec("r3", "R3", "bool", bool(components[5])),
            FieldSpec("adjust", "Adjust tie", "bool", bool(getattr(constraint, "adjust", False))),
            FieldSpec("distance", "Tie distance", "float", float(getattr(constraint, "distance", 0.0) or 0.0), minimum=0.0),
        ), parent, width=580, allow_apply=True)

    def values(self):
        values = super().values()
        kind = ConstraintType.coerce(values["constraint_type"])
        values["constraint_type"] = kind
        master_id = values.pop("master_id")
        slave_id = values.pop("slave_id")
        values["master"] = self.master_refs.get(master_id, ("", ConstraintReference(ConstraintReferenceKind.REFERENCE_POINT, EntityRef(str(master_id or ""), "ReferencePoint"))))[1]
        values["slave"] = self.slave_refs.get(slave_id, ("", ConstraintReference(ConstraintReferenceKind.SURFACE, EntityRef(str(slave_id or "")))))[1]
        values["components"] = tuple(int(values.pop(key)) for key in ("u1", "u2", "u3", "r1", "r2", "r3"))
        if kind != ConstraintType.TIE:
            values["adjust"] = None
            values["distance"] = None
        return values

    def validate(self):
        values = self.values()
        name = values["name"]
        allowed = [item for item in self.existing_names if not self.constraint or item.casefold() != self.constraint.name.casefold()]
        if not is_unique(name, allowed):
            QMessageBox.warning(self, "Duplicate name", f"A constraint named '{name}' already exists.")
            return False
        if not values["master"].ref.entity_id or not values["slave"].ref.entity_id:
            QMessageBox.warning(self, "Missing reference", "Create or select master and slave references.")
            return False
        return True

    def prepare_new(self, default_name, existing_names):
        self.constraint = None
        self.existing_names = tuple(existing_names)
        self._editors["name"].setText(default_name)
        self._editors["master_id"].clear()
        self._editors["slave_id"].clear()


def _reference_map(values, fallback):
    result = {}
    for value in values:
        if isinstance(value, tuple) and len(value) == 2 and isinstance(value[1], ConstraintReference):
            label, reference = str(value[0]), value[1]
        elif isinstance(value, ConstraintReference):
            reference = value
            label = reference.ref.legacy_name or reference.ref.entity_id
        else:
            kind = _kind_for_entity(value, fallback)
            reference = ConstraintReference(kind, EntityRef.of(value, kind.value.replace(" ", "")))
            label = getattr(value, "name", str(value))
        key = reference.ref.entity_id or reference.ref.legacy_name
        result[key] = (label, reference)
    return result


def _kind_for_entity(value, fallback):
    region_type = str(getattr(value, "region_type", ""))
    return ConstraintReferenceKind.coerce(region_type) if region_type else fallback


def _first(values):
    return next(iter(values), "")
