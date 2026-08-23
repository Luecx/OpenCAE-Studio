"""Provides the analysis-step editor using shared fields and checked entity lists."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QLineEdit, QMessageBox, QSpinBox, QVBoxLayout

from opencae.ui.templates import (
    CheckList,
    SectionHeading,
    apply_primary_control_height,
    dialog_buttons,
    field_block,
    field_row,
)


class StepDialog(QDialog):
    """Edit one analysis step and the loads/supports active during that step."""

    def __init__(self, step, loads, supports, parent=None, existing_names=()):
        """Build type-dependent step settings plus reusable checked entity selectors."""
        super().__init__(parent)
        self.step = step
        self.existing_names = tuple(existing_names)
        self.setWindowTitle(f"Edit {step.name}")
        self.setMinimumSize(680, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(16)

        self.name = QLineEdit(step.name)
        apply_primary_control_height(self.name)
        self.modes = QSpinBox()
        self.modes.setRange(1, 100000)
        self.modes.setValue(step.number_of_modes)
        apply_primary_control_height(self.modes)

        if step.step_type in {"Eigenfrequency", "Linear Buckling"}:
            root.addWidget(
                field_row(
                    field_block("Name", self.name),
                    field_block("Number of modes", self.modes),
                )
            )
        else:
            root.addWidget(field_block("Name", self.name))

        root.addWidget(SectionHeading("Active Entities"))
        support_ids = [ref.entity_id for ref in step.support_refs]
        self.supports = CheckList(supports, support_ids)
        support_field = field_block("Active supports", self.supports)

        self.loads = None
        if step.uses_loads:
            load_ids = [ref.entity_id for ref in step.load_refs]
            self.loads = CheckList(loads, load_ids)
            root.addWidget(
                field_row(
                    support_field,
                    field_block("Active loads", self.loads),
                )
            )
        else:
            root.addWidget(support_field)
        root.addStretch(1)

        buttons = dialog_buttons()
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _accept(self) -> None:
        """Validate unique naming before accepting the step edits."""
        from opencae.model.naming import is_unique

        if not is_unique(self.name.text(), self.existing_names, self.step.name):
            QMessageBox.warning(
                self,
                "Duplicate name",
                f"A step named '{self.name.text().strip()}' already exists.",
            )
            return
        self.accept()

    def values(self) -> dict:
        """Return edited step settings and IDs of all checked entities."""
        return {
            "name": self.name.text().strip(),
            "number_of_modes": self.modes.value(),
            "support_ids": self.supports.selected_values(),
            "load_ids": self.loads.selected_values() if self.loads else [],
        }
