from PyQt6.QtWidgets import QMessageBox

from opencae.model.entities.constraints import ConstraintReference, ConstraintReferenceKind, ConstraintType
from opencae.model.naming import is_unique
from opencae.ui.core.fields import FieldSpec
from opencae.ui.core.form_dialog import FormDialog


class ConstraintDialog(FormDialog):
    def __init__(self, masters=(), slaves=(), create_master=None, create_slave=None, parent=None,
                 default_name="Constraint-1", existing_names=(), initial_type=ConstraintType.KINEMATIC,
                 constraint=None):
        self.existing_names = tuple(existing_names); self.constraint = constraint
        self.master_refs = _reference_map(masters, ConstraintReferenceKind.REFERENCE_POINT)
        self.slave_refs = _reference_map(slaves, ConstraintReferenceKind.UNKNOWN)
        current_master = getattr(getattr(constraint, "master", None), "name", "")
        current_slave = getattr(getattr(constraint, "slave", None), "name", "")
        super().__init__("Edit Constraint" if constraint else "Create Constraint", (
            FieldSpec("name", "Name", "text", getattr(constraint, "name", default_name)),
            FieldSpec("constraint_type", "Type", "choice", str(getattr(constraint, "constraint_type", initial_type)), tuple(item.value for item in ConstraintType)),
            FieldSpec("master", "Master / control", "reference", current_master or _first(self.master_refs), tuple(self.master_refs), create_callback=create_master),
            FieldSpec("slave", "Slave / region", "reference", current_slave or _first(self.slave_refs), tuple(self.slave_refs), create_callback=create_slave),
        ), parent, width=580)

    def values(self):
        values = super().values(); values["constraint_type"] = ConstraintType.coerce(values["constraint_type"])
        values["master"] = self.master_refs.get(values["master"], ConstraintReference(values["master"], ConstraintReferenceKind.REFERENCE_POINT))
        values["slave"] = self.slave_refs.get(values["slave"], ConstraintReference(values["slave"], ConstraintReferenceKind.SURFACE))
        return values

    def accept(self):
        values = self.values(); name = values["name"]
        allowed = [item for item in self.existing_names if not self.constraint or item.casefold() != self.constraint.name.casefold()]
        if not is_unique(name, allowed): QMessageBox.warning(self, "Duplicate name", f"A constraint named '{name}' already exists."); return
        if not values["master"].name or not values["slave"].name: QMessageBox.warning(self, "Missing reference", "Create or select master and slave references."); return
        super().accept()


def _reference_map(values, fallback):
    result = {}
    for value in values:
        reference = value if isinstance(value, ConstraintReference) else ConstraintReference(str(value), fallback)
        result[reference.name] = reference
    return result


def _first(values): return next(iter(values), "")
