"""Edits the analysis and design-domain regions of a topology optimization."""

from copy import deepcopy

from PyQt6.QtWidgets import QFormLayout, QGroupBox, QMessageBox

from opencae.model.core import EntityRef
from opencae.model.entities.optimization import TopologyOptimization
from opencae.model.selection import RegionProjection, RegionRequirement
from opencae.ui.core.named_entity_dialog import NamedEntityDialog
from opencae.ui.core.widgets import CompactRegionSelector, ReferenceSelector


class TopologyOptimizationDialog(NamedEntityDialog):
    """Create or edit the top-level topology optimization definition."""

    def __init__(
        self,
        project,
        value=None,
        *,
        pick_callback=None,
        options=(),
        existing_names=(),
        parent=None,
    ):
        entity = value or TopologyOptimization(name="Topology Optimization-1")
        super().__init__(
            "Topology Optimization",
            entity,
            existing_names=existing_names,
            parent=parent,
            width=610,
        )
        analyses = [
            (analysis.name, analysis.id)
            for analysis in project.analyses
            if any(step.step_type == "Linear Static" for step in analysis.steps)
        ]
        self.analysis = ReferenceSelector(
            analyses,
            self.value.analysis_ref.entity_id,
        )
        self.form.addRow("Analysis", self.analysis)

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
        self.add_widget(regions)
        self.finish()

    def result(self):
        candidate = self.apply_name(deepcopy(self.value))
        candidate.analysis_ref = EntityRef(
            str(self.analysis.currentValue() or ""),
            "Analysis",
        )
        candidate.design_domain = self.design.definition()
        candidate.frozen_solid = self.solid.definition()
        candidate.frozen_void = self.void.definition()
        return candidate

    def validate(self) -> bool:
        if not super().validate():
            return False
        if not self.analysis.currentValue():
            QMessageBox.warning(
                self,
                "Missing analysis",
                "Select a Linear Static analysis.",
            )
            return False
        if self.design.definition().empty:
            QMessageBox.warning(
                self,
                "Missing design domain",
                "Select at least one design-domain element region.",
            )
            return False
        return True
