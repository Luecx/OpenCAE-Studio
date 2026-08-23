"""Edits planar or rotational topology symmetry using shared reference picking."""

from copy import deepcopy

from PyQt6.QtWidgets import QCheckBox, QMessageBox, QSpinBox

from opencae.model.entities.optimization import SymmetryType, TopologySymmetry
from opencae.model.selection import SelectableKind
from opencae.ui.core.named_entity_dialog import NamedEntityDialog
from opencae.ui.core.widgets import ChevronComboBox, PickReference
from opencae.ui.templates import (
    SectionHeading,
    apply_primary_control_height,
    field_block,
    field_row,
)


class TopologySymmetryDialog(NamedEntityDialog):
    """Create or edit a symmetry reference and rotational occurrence count."""

    def __init__(
        self,
        value=None,
        *,
        pick_reference=None,
        clear_preview=None,
        existing_names=(),
        parent=None,
    ):
        """Build the symmetry definition while preserving viewport-pick lifecycle."""
        entity = value or TopologySymmetry(name="Symmetry-1")
        super().__init__(
            "Topology Symmetry",
            entity,
            existing_names=existing_names,
            parent=parent,
            width=620,
        )
        self._pick_reference = pick_reference
        self._clear_preview = clear_preview

        self.kind = ChevronComboBox()
        self.kind.addItem("Planar", SymmetryType.PLANAR.value)
        self.kind.addItem("Rotational", SymmetryType.ROTATIONAL.value)
        current = self.kind.findData(self.value.symmetry_type.value)
        self.kind.setCurrentIndex(max(current, 0))
        self.kind.currentIndexChanged.connect(self._kind_changed)

        self.reference = PickReference(self._allowed_kinds())
        self.reference.set_reference(self.value.reference or None)
        self.reference.pick_requested.connect(self._request_pick)
        self.reference.cancel_requested.connect(self._cancel_pick)
        self.reference.changed.connect(self._reference_changed)

        self.occurrences = QSpinBox()
        self.occurrences.setRange(2, 128)
        self.occurrences.setValue(self.value.occurrences)
        apply_primary_control_height(self.occurrences)

        self.enabled = QCheckBox("Enabled")
        self.enabled.setChecked(self.value.enabled)

        self.add_widget(SectionHeading("Symmetry Definition"))
        self.add_widget(
            field_row(
                field_block("Type", self.kind),
                field_block("Occurrences", self.occurrences),
            )
        )
        self.add_widget(field_block("Reference", self.reference))
        self.add_widget(self.enabled)

        self.finished.connect(lambda _code: self._cleanup())
        self._kind_changed()
        self.finish()

    def result(self):
        """Return a copied symmetry entity populated from the editor state."""
        candidate = self.apply_name(deepcopy(self.value))
        candidate.symmetry_type = SymmetryType(self.kind.currentData())
        candidate.reference = self.reference.reference() or {}
        candidate.occurrences = (
            2
            if candidate.symmetry_type == SymmetryType.PLANAR
            else self.occurrences.value()
        )
        candidate.enabled = self.enabled.isChecked()
        return candidate

    def validate(self) -> bool:
        """Require a geometry or datum reference before committing symmetry."""
        if not super().validate():
            return False
        if not self.reference.reference():
            QMessageBox.warning(
                self,
                "Missing symmetry reference",
                "Pick a datum or geometry reference for this symmetry.",
            )
            return False
        return True

    def _kind_changed(self, *_):
        """Update occurrence availability and accepted reference kinds by symmetry type."""
        planar = self.kind.currentData() == SymmetryType.PLANAR.value
        self.occurrences.setEnabled(not planar)
        if planar:
            self.occurrences.setValue(2)
        self.reference.allowed = tuple(self._allowed_kinds())
        current = self.reference.reference()
        if current and current.get("kind") not in self._allowed_reference_names():
            self.reference.set_reference(None)

    def _allowed_kinds(self):
        """Return viewport selectable kinds valid for the active symmetry type."""
        if self.kind.currentData() == SymmetryType.PLANAR.value:
            return (
                SelectableKind.GEOMETRY_FACE,
                SelectableKind.DATUM_PLANE,
            )
        return (
            SelectableKind.GEOMETRY_EDGE,
            SelectableKind.DATUM_VECTOR,
        )

    def _allowed_reference_names(self):
        """Return serialized reference-kind names accepted by the active type."""
        if self.kind.currentData() == SymmetryType.PLANAR.value:
            return {"face", "datum_plane"}
        return {"edge", "datum_vector"}

    def _request_pick(self, _allowed, done, finished):
        """Delegate a symmetry-aware viewport pick to the controller callback."""
        if self._pick_reference is None:
            finished()
            return
        self._pick_reference(
            SymmetryType(self.kind.currentData()),
            done,
            finished,
        )

    def _cancel_pick(self):
        """Cancel an active viewport context pick when the field is toggled off."""
        owner = self.window()
        viewport = getattr(owner.parentWidget(), "viewport", None)
        if viewport is not None:
            viewport.cancel_context_pick()

    def _reference_changed(self):
        """Clear a stale preview when the selected symmetry reference is removed."""
        if self.reference.reference() is None and self._clear_preview:
            self._clear_preview()

    def _cleanup(self):
        """Remove transient symmetry preview state when the dialog finishes."""
        if self._clear_preview:
            self._clear_preview()
