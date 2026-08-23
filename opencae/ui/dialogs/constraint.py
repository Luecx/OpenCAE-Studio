"""Provides the Assembly constraint editor using shared labelled-field templates."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QLineEdit, QMessageBox, QVBoxLayout, QWidget

from opencae.model.entities.constraints import (
    ConstraintType,
    constraint_region_requirement,
    direct_control_point_error,
)
from opencae.model.naming import is_unique
from opencae.model.selection import RegionDefinition
from opencae.ui.core.apply_dialog import ApplyDialog
from opencae.ui.core.widgets import ChevronComboBox, CompactRegionSelector
from opencae.ui.templates import (
    CheckGrid,
    NumericUnitInput,
    SectionHeading,
    apply_primary_control_height,
    dialog_buttons,
    field_block,
    field_row,
)


class ConstraintDialog(ApplyDialog):
    """Create or edit Assembly constraints while preserving viewport-pick previews."""

    preview_changed = pyqtSignal(object, object)

    def __init__(
        self,
        project,
        options=(),
        pick_callback=None,
        save_callback=None,
        parent=None,
        default_name="Constraint-1",
        existing_names=(),
        initial_type=ConstraintType.KINEMATIC,
        constraint=None,
        validator=None,
        units=None,
    ):
        """Build the constraint definition and its type-dependent option sections."""
        super().__init__(parent)
        self.project = project
        self.existing_names = tuple(existing_names)
        self.constraint = constraint
        self.validator = validator
        self.pick_callback = pick_callback
        self.save_callback = save_callback
        self.units = units or getattr(getattr(parent, "controllers", None), "units", None)

        self.setWindowTitle("Edit Constraint" if constraint else "Create Constraint")
        self.setMinimumSize(760, 560)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(16)

        self.name = QLineEdit(getattr(constraint, "name", default_name))
        apply_primary_control_height(self.name)
        self.kind = ChevronComboBox()
        self.kind.setMinimumWidth(0)
        for value in ConstraintType:
            self.kind.addItem(value.value, value.value)
        current_kind = str(getattr(constraint, "constraint_type", initial_type))
        self.kind.setCurrentIndex(max(0, self.kind.findData(current_kind)))
        apply_primary_control_height(self.kind)
        root.addWidget(
            field_row(
                field_block("Name", self.name),
                field_block("Type", self.kind),
            )
        )

        root.addWidget(SectionHeading("Constraint Regions"))
        master = _master_definition(constraint)
        slave = _slave_definition(constraint)
        self.master = CompactRegionSelector(
            project,
            master,
            options,
            lambda owner, done, finished: self._pick(
                "master", owner, done, finished
            ),
            lambda owner, definition: self._save("master", owner, definition),
        )
        self.slave = CompactRegionSelector(
            project,
            slave,
            options,
            lambda owner, done, finished: self._pick(
                "slave", owner, done, finished
            ),
            lambda owner, definition: self._save("slave", owner, definition),
        )
        self.master_field = field_block("Master / control", self.master)
        self.slave_field = field_block("Slave / body", self.slave)
        root.addWidget(self.master_field)
        root.addWidget(self.slave_field)

        components = tuple(getattr(constraint, "components", (1, 1, 1, 1, 1, 1)))
        self.component_section = _section_container(root, "Degrees of Freedom")
        self.components = CheckGrid(
            ("U1", "U2", "U3", "R1", "R2", "R3"),
            components,
            columns=3,
        )
        self.component_section.layout().addWidget(self.components)

        self.tie_section = _section_container(root, "Tie Options")
        self.adjust = QCheckBox("Adjust slave nodes to the master surface")
        self.adjust.setChecked(bool(getattr(constraint, "adjust", False)))
        distance_unit = self.units.symbol("length") if self.units is not None else ""
        self.distance = NumericUnitInput(
            float(getattr(constraint, "distance", 0.0) or 0.0),
            distance_unit,
            minimum=0.0,
            maximum=1e30,
            decimals=12,
        )
        self.tie_section.layout().addWidget(
            field_row(
                field_block("Adjustment", self.adjust),
                field_block("Tie distance", self.distance),
            )
        )
        root.addStretch(1)

        buttons = dialog_buttons(include_apply=True)
        self.bind_buttons(buttons, True)
        root.addWidget(buttons)

        self.kind.currentIndexChanged.connect(self._update_type)
        self.master.value_changed.connect(lambda _value: self._emit_preview())
        self.slave.value_changed.connect(lambda _value: self._emit_preview())
        self._update_type()

    def _pick(self, role, owner, done, finished):
        """Delegate one constraint-side viewport pick to the owning controller."""
        if self.pick_callback:
            return self.pick_callback(
                self.constraint_type(), role, owner, done, finished
            )
        return None

    def _save(self, role, owner, definition):
        """Delegate saving a selected region when the controller exposes that action."""
        if self.save_callback:
            return self.save_callback(
                self.constraint_type(), role, owner, definition
            )
        return None

    def constraint_type(self):
        """Return the currently selected canonical constraint type."""
        return ConstraintType.coerce(self.kind.currentData())

    def _update_type(self) -> None:
        """Apply type-specific region requirements, labels, and option visibility."""
        # A pick policy belongs to one concrete type. End a running session
        # before changing requirements so the viewport cannot return stale hits.
        self.master.finish_pick()
        self.slave.finish_pick()
        kind = self.constraint_type()
        tie = kind == ConstraintType.TIE
        coupling = kind in {ConstraintType.KINEMATIC, ConstraintType.DISTRIBUTING}
        self.master.set_requirement(constraint_region_requirement(kind, "master"))
        self.slave.set_requirement(constraint_region_requirement(kind, "slave"))
        master_label, slave_label = {
            ConstraintType.KINEMATIC: ("Control point", "Coupled region"),
            ConstraintType.DISTRIBUTING: ("Control point", "Distributed region"),
            ConstraintType.TIE: ("Master surface", "Slave surface"),
            ConstraintType.RIGID_BODY: ("Reference point", "Rigid body region"),
        }.get(kind, ("Master", "Slave"))
        self.master_field.set_label(master_label)
        self.slave_field.set_label(slave_label)
        self.component_section.setVisible(coupling)
        self.tie_section.setVisible(tie)

        # Direct control points are visual selections, whereas tie masters may
        # intentionally use the extended named-region editor.
        self.master.set_extended_visible(tie)
        self.slave.set_extended_visible(True)
        if (coupling or kind == ConstraintType.RIGID_BODY) and not self.master.definition().empty:
            if direct_control_point_error(self.master.definition()):
                self.master.clear()
        self._emit_preview()

    def _emit_preview(self) -> None:
        """Publish both current region definitions for persistent viewport highlighting."""
        self.preview_changed.emit(self.master.definition(), self.slave.definition())

    def preview_definitions(self):
        """Return master/control and slave/body definitions for initial preview setup."""
        return self.master.definition(), self.slave.definition()

    def values(self) -> dict:
        """Return constructor values for the active constraint type."""
        kind = self.constraint_type()
        values = {"name": self.name.text().strip(), "constraint_type": kind}
        if kind in {ConstraintType.KINEMATIC, ConstraintType.DISTRIBUTING}:
            values.update(
                control_point=self.master.definition(),
                slave=self.slave.definition(),
                components=tuple(int(value) for value in self.components.values()),
            )
        elif kind == ConstraintType.TIE:
            values.update(
                master=self.master.definition(),
                slave=self.slave.definition(),
                adjust=self.adjust.isChecked(),
                distance=self.distance.value(),
            )
        elif kind == ConstraintType.RIGID_BODY:
            values.update(reference=self.master.definition(), body=self.slave.definition())
        else:
            values.update(master=self.master.definition(), slave=self.slave.definition())
        return values

    def validate(self) -> bool:
        """Validate naming and both region definitions before a constraint is committed."""
        allowed = [
            item
            for item in self.existing_names
            if not self.constraint or item.casefold() != self.constraint.name.casefold()
        ]
        if not is_unique(self.name.text().strip(), allowed):
            QMessageBox.warning(
                self,
                "Duplicate name",
                f"A constraint named '{self.name.text().strip()}' already exists.",
            )
            return False
        if self.master.definition().empty or self.slave.definition().empty:
            QMessageBox.warning(
                self,
                "Missing target",
                "Select both master/control and slave/body regions.",
            )
            return False
        if self.validator:
            error = self.validator(self.values())
            if error:
                QMessageBox.warning(self, "Invalid constraint regions", error)
                return False
        return True

    def prepare_new(self, default_name, existing_names) -> None:
        """Reset selection and naming state after Apply creates a constraint."""
        self.constraint = None
        self.existing_names = tuple(existing_names)
        self.name.setText(default_name)
        self.master.clear()
        self.slave.clear()


def _section_container(root: QVBoxLayout, title: str) -> QWidget:
    """Create one dynamic dialog section whose heading hides with its content."""
    host = QWidget()
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)
    layout.addWidget(SectionHeading(title))
    root.addWidget(host)
    return host


def _master_definition(constraint):
    """Return the stored master/control definition across supported constraint types."""
    if constraint is None:
        return RegionDefinition()
    return getattr(
        constraint,
        "control_point",
        getattr(constraint, "reference", getattr(constraint, "master", RegionDefinition())),
    )


def _slave_definition(constraint):
    """Return the stored slave/body definition across supported constraint types."""
    if constraint is None:
        return RegionDefinition()
    return getattr(constraint, "body", getattr(constraint, "slave", RegionDefinition()))
