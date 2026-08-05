"""Edits the independent density-coupling and sensitivity filter radii."""

from copy import deepcopy

from PyQt6.QtWidgets import QCheckBox, QGroupBox, QLabel, QMessageBox, QVBoxLayout

from opencae.model.entities.optimization import FilterRadius, TopologyFilterSettings
from opencae.ui.core.named_entity_dialog import NamedEntityDialog
from opencae.ui.core.widgets import AutomaticManualValueEditor


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
            width=590,
        )
        self.enabled = QCheckBox("Enable filtering")
        self.enabled.setChecked(self.value.enabled)
        self.weighted = QCheckBox("Density-weighted sensitivity filter")
        self.weighted.setChecked(self.value.density_weighted_sensitivities)
        self.form.addRow("", self.enabled)
        self.form.addRow("", self.weighted)

        self.density_radius = self._radius_group(
            "Density / constraint coupling radius — local",
            "Builds the physical-density and symmetry coupling matrix. "
            "Automatic default: 2.5 × the minimum positive centroid distance.",
            self.value.density_constraint_radius,
        )
        self.sensitivity_radius = self._radius_group(
            "Sensitivity-filter radius — broader",
            "Filters compliance sensitivities only. Automatic default: "
            "5 × the minimum positive centroid distance.",
            self.value.sensitivity_radius,
        )
        self.finish()

    def _radius_group(self, title, description, value):
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        note = QLabel(description)
        note.setWordWrap(True)
        note.setObjectName("MutedLabel")
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
        layout.addWidget(note)
        layout.addWidget(editor)
        self.add_widget(group)
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
        sensitivity_value = (
            sensitivity.factor if sensitivity.automatic else sensitivity.value
        )
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
