"""Edits one region-scoped response used by topology objectives or constraints."""

from copy import deepcopy

from PyQt6.QtWidgets import QLabel, QMessageBox

from opencae.model.entities.optimization import OptimizationResponse, ResponseType
from opencae.model.selection import RegionProjection, RegionRequirement
from opencae.ui.core.named_entity_dialog import NamedEntityDialog
from opencae.ui.core.widgets import ChevronComboBox, CompactRegionSelector


class OptimizationResponseDialog(NamedEntityDialog):
    """Create or edit an optimization response and its element region."""

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
        entity = value or OptimizationResponse(
            name="Response-1",
            response_type=ResponseType.STIFFNESS_ENERGY,
        )
        super().__init__(
            "Optimization Response",
            entity,
            existing_names=existing_names,
            parent=parent,
            width=580,
        )
        self.kind = ChevronComboBox()
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
        self.form.addRow("Type", self.kind)
        self.form.addRow("Region", self.region)

        note = QLabel(
            "Stiffness Energy uses the complete model in the current OC solver. "
            "Volume and mass responses may use arbitrary element regions."
        )
        note.setWordWrap(True)
        note.setObjectName("MutedLabel")
        self.add_widget(note)
        self.finish()

    def result(self):
        candidate = self.apply_name(deepcopy(self.value))
        candidate.response_type = ResponseType(self.kind.currentData())
        candidate.region = self.region.definition()
        return candidate

    def validate(self) -> bool:
        if not super().validate():
            return False
        if self.region.definition().empty:
            QMessageBox.warning(
                self,
                "Missing response region",
                "Select at least one element region for this response.",
            )
            return False
        return True
