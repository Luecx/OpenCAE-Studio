"""Edits planar or rotational topology symmetry using shared reference picking."""

from copy import deepcopy

from PyQt6.QtWidgets import QMessageBox

from opencae.model.entities.optimization import SymmetryType, TopologySymmetry
from opencae.model.selection import SelectableKind
from opencae.ui.composites.controls import ControlPickReference
from opencae.ui.core.named_entity_dialog import NamedEntityDialog
from opencae.ui.primitives.checks import CheckForm
from opencae.ui.primitives.inputs import InputFormInteger
from opencae.ui.primitives.selects import SelectForm
from opencae.ui.templates import SectionHeading, field_block, field_row


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

        self.kind = SelectForm()
        self.kind.addItem("Planar", SymmetryType.PLANAR.value)
        self.kind.addItem("Rotational", SymmetryType.ROTATIONAL.value)
        current = self.kind.findData(self.value.symmetry_type.value)
        self.kind.setCurrentIndex(max(current, 0))
        self.kind.currentIndexChanged.connect(self._kind_changed)

        self.reference = ControlPickReference(self._allowed_kinds())
        self.reference.set_reference(self.value.reference or None)
        self.reference.pick_requested.connect(self._request_pick)
        self.reference.cancel_requested.connect(self._cancel_pick)
        self.reference.changed.connect(self._reference_changed)

        self.occurrences = InputFormInteger(
            self.value.occurrences,
            minimum=2,
            maximum=128,
        )

        self.enabled = CheckForm("Enabled", checked=self.value.enabled)

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
        candidate = self.apply_name(deepcopy(self.value))
        candidate.symmetry_type = SymmetryType(self.kind.currentData())
        candidate.reference = self.reference.reference() or {}
        candidate.occurrences = (
            2 if candidate.symmetry_type == SymmetryType.PLANAR else self.occurrences.value()
        )
        candidate.enabled = self.enabled.isChecked()
        return candidate

    def validate(self) -> bool:
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
        planar = self.kind.currentData() == SymmetryType.PLANAR.value
        self.occurrences.setEnabled(not planar)
        if planar:
            self.occurrences.setValue(2)
        self.reference.allowed = tuple(self._allowed_kinds())
        current = self.reference.reference()
        if current and current.get("kind") not in self._allowed_reference_names():
            self.reference.set_reference(None)

    def _allowed_kinds(self):
        if self.kind.currentData() == SymmetryType.PLANAR.value:
            return (SelectableKind.GEOMETRY_FACE, SelectableKind.DATUM_PLANE)
        return (SelectableKind.GEOMETRY_EDGE, SelectableKind.DATUM_VECTOR)

    def _allowed_reference_names(self):
        if self.kind.currentData() == SymmetryType.PLANAR.value:
            return {"face", "datum_plane"}
        return {"edge", "datum_vector"}

    def _request_pick(self, _allowed, done, finished):
        if self._pick_reference is None:
            finished()
            return
        self._pick_reference(SymmetryType(self.kind.currentData()), done, finished)

    def _cancel_pick(self):
        owner = self.window()
        viewport = getattr(owner.parentWidget(), "viewport", None)
        if viewport is not None:
            viewport.cancel_context_pick()

    def _reference_changed(self):
        if self.reference.reference() is None and self._clear_preview:
            self._clear_preview()

    def _cleanup(self):
        if self._clear_preview:
            self._clear_preview()
