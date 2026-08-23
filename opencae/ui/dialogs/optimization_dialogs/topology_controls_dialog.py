"""Edits iteration, SIMP, convergence and output controls for topology runs."""

from copy import deepcopy

from PyQt6.QtWidgets import QMessageBox

from opencae.model.entities.optimization import TopologyControls
from opencae.ui.core.fields import FieldSpec, create_editor, editor_value
from opencae.ui.core.named_entity_dialog import NamedEntityDialog
from opencae.ui.templates import SectionHeading, field_block, field_row


class TopologyControlsDialog(NamedEntityDialog):
    """Create or edit the numerical controls used by the topology runner."""

    def __init__(
        self,
        value: TopologyControls,
        *,
        existing_names=(),
        parent=None,
    ):
        """Build grouped numerical controls from the shared editor primitives."""
        super().__init__(
            "Topology Optimization Controls",
            value,
            existing_names=existing_names,
            parent=parent,
            width=680,
        )
        specs = {
            "maximum_iterations": FieldSpec(
                "maximum_iterations",
                "Maximum iterations",
                kind="int",
                default=value.maximum_iterations,
                minimum=1,
                maximum=100000,
            ),
            "minimum_density": FieldSpec(
                "minimum_density",
                "Minimum density",
                kind="float",
                default=value.minimum_density,
                minimum=1.0e-9,
                maximum=0.999999,
                decimals=9,
            ),
            "initial_density": FieldSpec(
                "initial_density",
                "Initial density",
                kind="float",
                default=value.initial_density,
                minimum=1.0e-9,
                maximum=1.0,
                decimals=6,
            ),
            "simp_exponent": FieldSpec(
                "simp_exponent",
                "SIMP exponent",
                kind="float",
                default=value.simp_exponent,
                minimum=0.01,
                maximum=100.0,
                decimals=6,
            ),
            "move_limit": FieldSpec(
                "move_limit",
                "Move limit",
                kind="float",
                default=value.move_limit,
                minimum=1.0e-6,
                maximum=1.0,
                decimals=6,
            ),
            "density_change_tolerance": FieldSpec(
                "density_change_tolerance",
                "Density-change tolerance",
                kind="float",
                default=value.density_change_tolerance,
                minimum=1.0e-12,
                maximum=1.0,
                decimals=9,
            ),
            "objective_tolerance": FieldSpec(
                "objective_tolerance",
                "Objective tolerance",
                kind="float",
                default=value.objective_tolerance,
                minimum=1.0e-12,
                maximum=1.0,
                decimals=9,
            ),
            "bisection_tolerance": FieldSpec(
                "bisection_tolerance",
                "Bisection tolerance",
                kind="float",
                default=value.bisection_tolerance,
                minimum=1.0e-15,
                maximum=1.0,
                decimals=12,
            ),
            "maximum_bisection_steps": FieldSpec(
                "maximum_bisection_steps",
                "Maximum bisection steps",
                kind="int",
                default=value.maximum_bisection_steps,
                minimum=1,
                maximum=10000,
            ),
            "save_every": FieldSpec(
                "save_every",
                "Save every N iterations",
                kind="int",
                default=value.save_every,
                minimum=1,
                maximum=10000,
            ),
            "keep_solver_files": FieldSpec(
                "keep_solver_files",
                "Keep FEMaster .res/.frd files",
                kind="bool",
                default=value.keep_solver_files,
            ),
        }
        self.editors = {
            key: create_editor(spec)
            for key, spec in specs.items()
        }

        self.add_widget(SectionHeading("Iteration Controls"))
        self.add_widget(
            field_row(
                field_block(specs["maximum_iterations"].label, self.editors["maximum_iterations"]),
                field_block(specs["save_every"].label, self.editors["save_every"]),
            )
        )

        self.add_widget(SectionHeading("Density and SIMP"))
        self.add_widget(
            field_row(
                field_block(specs["minimum_density"].label, self.editors["minimum_density"]),
                field_block(specs["initial_density"].label, self.editors["initial_density"]),
            )
        )
        self.add_widget(
            field_row(
                field_block(specs["simp_exponent"].label, self.editors["simp_exponent"]),
                field_block(specs["move_limit"].label, self.editors["move_limit"]),
            )
        )

        self.add_widget(SectionHeading("Convergence"))
        self.add_widget(
            field_row(
                field_block(
                    specs["density_change_tolerance"].label,
                    self.editors["density_change_tolerance"],
                ),
                field_block(
                    specs["objective_tolerance"].label,
                    self.editors["objective_tolerance"],
                ),
            )
        )
        self.add_widget(
            field_row(
                field_block(
                    specs["bisection_tolerance"].label,
                    self.editors["bisection_tolerance"],
                ),
                field_block(
                    specs["maximum_bisection_steps"].label,
                    self.editors["maximum_bisection_steps"],
                ),
            )
        )

        self.add_widget(SectionHeading("Output"))
        self.add_widget(self.editors["keep_solver_files"])
        self.finish()

    def result(self):
        """Return a copied controls entity populated from the current editors."""
        candidate = self.apply_name(deepcopy(self.value))
        for key, editor in self.editors.items():
            setattr(candidate, key, editor_value(editor))
        return candidate

    def validate(self) -> bool:
        """Reject an initial density below the configured minimum density."""
        if not super().validate():
            return False
        minimum = float(editor_value(self.editors["minimum_density"]))
        initial = float(editor_value(self.editors["initial_density"]))
        if initial < minimum:
            QMessageBox.warning(
                self,
                "Invalid densities",
                "Initial density must be greater than or equal to minimum density.",
            )
            return False
        return True
