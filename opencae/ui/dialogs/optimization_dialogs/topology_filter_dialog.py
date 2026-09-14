"""Edits the independent density-coupling and sensitivity filter radii."""

from copy import deepcopy

from PyQt6.QtWidgets import QMessageBox

from opencae.model.entities.optimization import FilterRadius, TopologyFilterSettings
from opencae.ui.core.named_entity_dialog import NamedEntityDialog
from opencae.ui.core.widgets import AutomaticManualValueEditor
from opencae.ui.primitives.checks import CheckForm
from opencae.ui.primitives.labels import LabelMuted
from opencae.ui.templates import SectionHeading


class TopologyFilterDialog(NamedEntityDialog):
    """Edit topology filter activation, weighting and both radius definitions."""

    def __init__(
        self,
        value: TopologyFilterSettings,
        *,
        existing_names=(),
        parent=None,
    ):
        super().__init__(
            "Topology Filters",
            value,
            existing_names=existing_names,
            parent=parent,
            width=640,
        )
        self.add_widget(SectionHeading("Filter Settings"))
        self.enabled = CheckForm("Enable filtering", checked=self.value.enabled)
        self.weighted = CheckForm(
            "Density-weighted sensitivity filter",
            checked=self.value.density_weighted_sensitivities,
        )
        self.add_widget(self.enabled)
        self.add_widget(self.weighted)

        self.density_radius = self._radius_section(
            "Density / Constraint Coupling Radius",
            "Builds the physical-density and symmetry coupling matrix. "
            "Automatic default: 2.5 × the minimum positive centroid distance.",
            self.value.density_constraint_radius,
        )
        self.sensitivity_radius = self._radius_section(
            "Sensitivity Filter Radius",
            "Filters compliance sensitivities only. Automatic default: "
            "5 × the minimum positive centroid distance.",
            self.value.sensitivity_radius,
        )
        self.finish()

    def _radius_section(self, title, description, value):
        self.add_widget(SectionHeading(title))
        note = LabelMuted(description)
        note.setWordWrap(True)
        self.add_widget(note)

        editor = AutomaticManualValueEditor(
            automatic=value.automatic,
            factor=value.factor,
            value=value.value,
            automatic_text="Automatic from minimum element spacing",
            factor_label="Factor × minimum distance",
            manual_text="Manual distance",
            value_label="Distance",
            factor_range=(1.0, 1000.0),
        )
        self.add_widget(editor)
        return editor

    def result(self):
        candidate = self.apply_name(deepcopy(self.value))
        candidate.enabled = self.enabled.isChecked()
        candidate.density_weighted_sensitivities = self.weighted.isChecked()
        candidate.density_constraint_radius = self._radius_value(self.density_radius)
        candidate.sensitivity_radius = self._radius_value(self.sensitivity_radius)
        return candidate

    def validate(self) -> bool:
        if not super().validate():
            return False
        density = self._radius_value(self.density_radius)
        sensitivity = self._radius_value(self.sensitivity_radius)
        comparable = density.automatic == sensitivity.automatic
        density_value = density.factor if density.automatic else density.value
        sensitivity_value = sensitivity.factor if sensitivity.automatic else sensitivity.value
        if self.enabled.isChecked() and comparable and sensitivity_value < density_value:
            QMessageBox.warning(
                self,
                "Invalid filter radii",
                "The sensitivity-filter radius must not be smaller than the "
                "density/constraint radius.",
            )
            return False
        return True

    @staticmethod
    def _radius_value(editor):
        automatic, factor, value = editor.values()
        return FilterRadius(automatic=automatic, factor=factor, value=value)
