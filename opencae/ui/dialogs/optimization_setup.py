from __future__ import annotations

from copy import deepcopy

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
)

from opencae.model.core import EntityRef
from opencae.model.entities.optimization import (
    ConstraintOperator,
    OptimizationConstraint,
    OptimizationObjective,
    OptimizationResponse,
    ResponseType,
    TopologyOptimization,
)
from opencae.model.selection import RegionProjection, RegionRequirement
from opencae.ui.core.widgets.compact_region_selector import CompactRegionSelector

from .optimization_common import EntityDialog

_RESOURCE_TYPES = {
    ResponseType.VOLUME,
    ResponseType.VOLUME_FRACTION,
    ResponseType.MASS,
    ResponseType.MASS_FRACTION,
}


class TopologyOptimizationDialog(EntityDialog):
    def __init__(self, project, value=None, *, pick_callback=None, options=(), parent=None):
        super().__init__("Topology Optimization", parent)
        self.value = deepcopy(value) if value else TopologyOptimization(
            name="Topology Optimization-1"
        )
        self.setMinimumWidth(610)
        form = QFormLayout()
        self.name = QLineEdit(self.value.name)
        self.analysis = QComboBox()
        for analysis in project.analyses:
            if any(step.step_type == "Linear Static" for step in analysis.steps):
                self.analysis.addItem(analysis.name, analysis.id)
        selected = self.value.analysis_ref.entity_id
        index = self.analysis.findData(selected)
        if index >= 0:
            self.analysis.setCurrentIndex(index)
        form.addRow("Name", self.name)
        form.addRow("Analysis", self.analysis)
        self.root.addLayout(form)

        requirement = RegionRequirement(
            RegionProjection.ELEMENTS,
            allowed_dimensions=(1, 2, 3),
            min_count=1,
        )
        self.design = CompactRegionSelector(
            project,
            self.value.design_domain,
            options,
            pick_callback,
            requirement=requirement,
            extended_title="Design-domain region",
        )
        self.solid = CompactRegionSelector(
            project,
            self.value.frozen_solid,
            options,
            pick_callback,
            requirement=requirement,
            extended_title="Frozen-solid region",
        )
        self.void = CompactRegionSelector(
            project,
            self.value.frozen_void,
            options,
            pick_callback,
            requirement=requirement,
            extended_title="Frozen-void region",
        )
        regions = QGroupBox("Design domains")
        region_form = QFormLayout(regions)
        region_form.addRow("Design domain", self.design)
        region_form.addRow("Frozen solid", self.solid)
        region_form.addRow("Frozen void", self.void)
        self.root.addWidget(regions)
        self.finish()

    def result(self):
        candidate = deepcopy(self.value)
        candidate.name = self.name.text().strip() or candidate.name
        candidate.analysis_ref = EntityRef(
            str(self.analysis.currentData() or ""), "Analysis"
        )
        candidate.design_domain = self.design.definition()
        candidate.frozen_solid = self.solid.definition()
        candidate.frozen_void = self.void.definition()
        return candidate


class OptimizationResponseDialog(EntityDialog):
    def __init__(self, project, value=None, *, pick_callback=None, options=(), parent=None):
        super().__init__("Optimization Response", parent)
        self.value = deepcopy(value) if value else OptimizationResponse(
            name="Response-1", response_type=ResponseType.STIFFNESS_ENERGY
        )
        self.setMinimumWidth(580)
        form = QFormLayout()
        self.name = QLineEdit(self.value.name)
        self.kind = QComboBox()
        for kind, label in (
            (ResponseType.VOLUME, "Volume"),
            (ResponseType.VOLUME_FRACTION, "Volume Fraction"),
            (ResponseType.MASS, "Mass"),
            (ResponseType.MASS_FRACTION, "Mass Fraction"),
            (ResponseType.STIFFNESS_ENERGY, "Stiffness Energy Measure"),
        ):
            self.kind.addItem(label, kind.value)
        current = self.kind.findData(self.value.response_type.value)
        self.kind.setCurrentIndex(max(current, 0))
        requirement = RegionRequirement(
            RegionProjection.ELEMENTS,
            allowed_dimensions=(1, 2, 3),
            min_count=1,
        )
        self.region = CompactRegionSelector(
            project,
            self.value.region,
            options,
            pick_callback,
            requirement=requirement,
            extended_title="Response region",
        )
        form.addRow("Name", self.name)
        form.addRow("Type", self.kind)
        form.addRow("Region", self.region)
        self.root.addLayout(form)
        note = QLabel(
            "Stiffness Energy uses the complete model in the current OC solver. "
            "Volume and mass responses may use arbitrary element regions."
        )
        note.setWordWrap(True)
        note.setObjectName("MutedLabel")
        self.root.addWidget(note)
        self.finish()

    def result(self):
        candidate = deepcopy(self.value)
        candidate.name = self.name.text().strip() or candidate.name
        candidate.response_type = ResponseType(self.kind.currentData())
        candidate.region = self.region.definition()
        return candidate


class OptimizationObjectiveDialog(EntityDialog):
    def __init__(self, optimization, value=None, parent=None):
        super().__init__("Optimization Objective", parent)
        self.value = deepcopy(value) if value else OptimizationObjective(
            name="Minimize Stiffness Energy"
        )
        form = QFormLayout()
        self.name = QLineEdit(self.value.name)
        self.response = QComboBox()
        for item in optimization.responses:
            if item.response_type == ResponseType.STIFFNESS_ENERGY:
                self.response.addItem(item.name, item.id)
        current = self.response.findData(self.value.response_ref.entity_id)
        if current >= 0:
            self.response.setCurrentIndex(current)
        self.sense = QComboBox()
        self.sense.addItem("Minimize", "minimize")
        form.addRow("Name", self.name)
        form.addRow("Response", self.response)
        form.addRow("Sense", self.sense)
        self.root.addLayout(form)
        self.finish()

    def result(self):
        candidate = deepcopy(self.value)
        candidate.name = self.name.text().strip() or candidate.name
        candidate.response_ref = EntityRef(
            str(self.response.currentData() or ""), "OptimizationResponse"
        )
        candidate.sense = "minimize"
        return candidate


class OptimizationConstraintDialog(EntityDialog):
    def __init__(self, optimization, value=None, parent=None):
        super().__init__("Optimization Constraint", parent)
        self.value = deepcopy(value) if value else OptimizationConstraint(
            name="Constraint-1"
        )
        form = QFormLayout()
        self.name = QLineEdit(self.value.name)
        self.response = QComboBox()
        for item in optimization.responses:
            if item.response_type in _RESOURCE_TYPES:
                self.response.addItem(item.name, item.id)
        current = self.response.findData(self.value.response_ref.entity_id)
        if current >= 0:
            self.response.setCurrentIndex(current)
        self.operator = QComboBox()
        self.operator.addItem(
            ConstraintOperator.LESS_EQUAL.value,
            ConstraintOperator.LESS_EQUAL.value,
        )
        current = self.operator.findData(self.value.operator.value)
        self.operator.setCurrentIndex(max(current, 0))
        self.limit = QDoubleSpinBox()
        self.limit.setDecimals(9)
        self.limit.setRange(1.0e-12, 1.0e30)
        self.limit.setValue(float(self.value.limit))
        self.active = QCheckBox("Enabled")
        self.active.setChecked(self.value.active)
        form.addRow("Name", self.name)
        form.addRow("Response", self.response)
        form.addRow("Operator", self.operator)
        form.addRow("Limit", self.limit)
        form.addRow("", self.active)
        self.root.addLayout(form)
        note = QLabel(
            "OC + bisection currently supports exactly one enabled <= resource constraint."
        )
        note.setWordWrap(True)
        note.setObjectName("MutedLabel")
        self.root.addWidget(note)
        self.finish()

    def result(self):
        candidate = deepcopy(self.value)
        candidate.name = self.name.text().strip() or candidate.name
        candidate.response_ref = EntityRef(
            str(self.response.currentData() or ""), "OptimizationResponse"
        )
        candidate.operator = ConstraintOperator(self.operator.currentData())
        candidate.limit = self.limit.value()
        candidate.active = self.active.isChecked()
        return candidate
