"""Sketcher inspector assembled exclusively from concrete primitive controls."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget

from opencae.model.entities.geometry import SketchFeatureMode
from opencae.ui.primitives.buttons.button_sketch_action import ButtonSketchAction
from opencae.ui.primitives.checks.check_sketch import CheckSketch
from opencae.ui.primitives.inputs.input_sketch_number import InputSketchNumber
from opencae.ui.primitives.inputs.input_sketch_text import InputSketchText
from opencae.ui.primitives.labels.label_sketch_field import LabelSketchField
from opencae.ui.primitives.labels.label_sketch_heading import LabelSketchHeading
from opencae.ui.primitives.labels.label_sketch_note import LabelSketchNote
from opencae.ui.primitives.lists.list_sketch_constraints import ListSketchConstraints
from opencae.ui.primitives.selects.select_sketch import SelectSketch
from opencae.ui.primitives.separators.separator_horizontal import SeparatorHorizontal


class PanelSketchInspector(QFrame):
    """Compact feature/constraint inspector matching the existing Sketcher chrome."""

    EXPOSED_CONTROLS = (
        "name_edit",
        "mode_combo",
        "operation_combo",
        "depth_label",
        "depth_spin",
        "angle_label",
        "angle_spin",
        "symmetric_check",
        "reverse_check",
        "axis_note",
        "constraint_list",
        "delete_constraint_button",
        "solve_button",
        "auto_constraints_check",
        "snap_grid_check",
        "snap_geometry_check",
        "show_dimensions_check",
    )

    def __init__(self, sketch, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SketchInspector")
        self.setMinimumWidth(250)
        self.setMaximumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        layout.addWidget(LabelSketchHeading("FEATURE", self))
        layout.addWidget(LabelSketchField("Name", self))
        self.name_edit = InputSketchText(parent=self)
        layout.addWidget(self.name_edit)

        layout.addWidget(LabelSketchField("Type", self))
        self.mode_combo = SelectSketch(self)
        self.mode_combo.addItems(tuple(mode.value for mode in SketchFeatureMode))
        layout.addWidget(self.mode_combo)

        layout.addWidget(LabelSketchField("Operation", self))
        self.operation_combo = SelectSketch(self)
        self.operation_combo.addItems(("New", "Add", "Cut", "Intersect"))
        layout.addWidget(self.operation_combo)

        self.depth_label = LabelSketchField("Depth", self)
        self.depth_spin = InputSketchNumber(
            minimum=1.0e-9,
            maximum=1.0e12,
            decimals=6,
            step=1.0,
            parent=self,
        )
        self.angle_label = LabelSketchField("Angle", self)
        self.angle_spin = InputSketchNumber(
            minimum=0.001,
            maximum=360.0,
            decimals=3,
            step=5.0,
            suffix="°",
            parent=self,
        )
        layout.addWidget(self.depth_label)
        layout.addWidget(self.depth_spin)
        layout.addWidget(self.angle_label)
        layout.addWidget(self.angle_spin)

        self.symmetric_check = CheckSketch("Symmetric about sketch plane", parent=self)
        self.reverse_check = CheckSketch("Reverse direction", parent=self)
        layout.addWidget(self.symmetric_check)
        layout.addWidget(self.reverse_check)

        self.axis_note = LabelSketchNote(
            "Revolve axis: X axis\nShown dash-dot in the sketch.", self
        )
        layout.addWidget(self.axis_note)

        layout.addWidget(SeparatorHorizontal(self))
        layout.addWidget(LabelSketchHeading("CONSTRAINTS & DIMENSIONS", self))
        self.constraint_list = ListSketchConstraints(self)
        layout.addWidget(self.constraint_list, 1)

        constraint_row = QHBoxLayout()
        self.delete_constraint_button = ButtonSketchAction("Remove", self)
        self.solve_button = ButtonSketchAction("Solve", self)
        constraint_row.addWidget(self.delete_constraint_button)
        constraint_row.addWidget(self.solve_button)
        layout.addLayout(constraint_row)

        layout.addWidget(SeparatorHorizontal(self))
        layout.addWidget(LabelSketchHeading("SKETCH OPTIONS", self))
        self.auto_constraints_check = CheckSketch(
            "Automatic H/V constraints", checked=True, parent=self
        )
        self.snap_grid_check = CheckSketch(
            "Snap to grid", checked=bool(sketch.snap_grid), parent=self
        )
        self.snap_geometry_check = CheckSketch(
            "Snap to geometry", checked=bool(sketch.snap_geometry), parent=self
        )
        self.show_dimensions_check = CheckSketch(
            "Show dimensions", checked=True, parent=self
        )
        layout.addWidget(self.auto_constraints_check)
        layout.addWidget(self.snap_grid_check)
        layout.addWidget(self.snap_geometry_check)
        layout.addWidget(self.show_dimensions_check)

    def expose_on(self, owner) -> None:
        """Publish the legacy control attributes expected by Sketcher behavior code."""
        for name in self.EXPOSED_CONTROLS:
            setattr(owner, name, getattr(self, name))
