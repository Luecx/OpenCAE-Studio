"""Edits iteration, SIMP, convergence and output controls for topology runs."""

from copy import deepcopy

from PyQt6.QtWidgets import QMessageBox

from opencae.model.entities.optimization import TopologyControls
from opencae.ui.core.fields import FieldSpec, create_editor, editor_value
from opencae.ui.core.named_entity_dialog import NamedEntityDialog


class TopologyControlsDialog(NamedEntityDialog):
    """Create or edit the numerical controls used by the topology runner."""

    def __init__(
        self,
        value: TopologyControls,
        *,
        existing_names=(),
        parent=None,
    ):
        super().__init__(
            "Topology Optimization Controls",
            value,
            existing_names=existing_names,
            parent=parent,
            width=520,
        )
        specs = (
            FieldSpec(
                "maximum_iterations",
                "Maximum iterations",
                kind="int",
                default=value.maximum_iterations,
                minimum=1,
                maximum=100000,
            ),
            FieldSpec(
                "minimum_density",
                "Minimum density",
                kind="float",
                default=value.minimum_density,
                minimum=1.0e-9,
                maximum=0.999999,
                decimals=9,
            ),
            FieldSpec(
                "initial_density",
                "Initial density",
                kind="float",
                default=value.initial_density,
                minimum=1.0e-9,
                maximum=1.0,
                decimals=6,
            ),
            FieldSpec(
                "simp_exponent",
                "SIMP exponent",
                kind="float",
                default=value.simp_exponent,
                minimum=0.01,
                maximum=100.0,
                decimals=6,
            ),
            FieldSpec(
                "move_limit",
                "Move limit",
                kind="float",
                default=value.move_limit,
                minimum=1.0e-6,
                maximum=1.0,
                decimals=6,
            ),
            FieldSpec(
                "density_change_tolerance",
                "Density-change tolerance",
                kind="float",
                default=value.density_change_tolerance,
                minimum=1.0e-12,
                maximum=1.0,
                decimals=9,
            ),
            FieldSpec(
                "objective_tolerance",
                "Objective tolerance",
                kind="float",
                default=value.objective_tolerance,
                minimum=1.0e-12,
                maximum=1.0,
                decimals=9,
            ),
            FieldSpec(
                "bisection_tolerance",
                "Bisection tolerance",
                kind="float",
                default=value.bisection_tolerance,
                minimum=1.0e-15,
                maximum=1.0,
                decimals=12,
            ),
            FieldSpec(
                "maximum_bisection_steps",
                "Maximum bisection steps",
                kind="int",
                default=value.maximum_bisection_steps,
                minimum=1,
                maximum=10000,
            ),
            FieldSpec(
                "save_every",
                "Save every N iterations",
                kind="int",
                default=value.save_every,
                minimum=1,
                maximum=10000,
            ),
            FieldSpec(
                "keep_solver_files",
                "Keep FEMaster .res/.frd files",
                kind="bool",
                default=value.keep_solver_files,
            ),
        )
        self.editors = {}
        for spec in specs:
            editor = create_editor(spec)
            self.editors[spec.key] = editor
            self.form.addRow(spec.label, editor)
        self.finish()

    def result(self):
        candidate = self.apply_name(deepcopy(self.value))
        for key, editor in self.editors.items():
            setattr(candidate, key, editor_value(editor))
        return candidate

    def validate(self) -> bool:
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
