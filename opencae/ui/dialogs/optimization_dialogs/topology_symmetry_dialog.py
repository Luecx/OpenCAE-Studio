"""Edits planar or rotational topology symmetry using shared reference picking."""

from copy import deepcopy

from PyQt6.QtWidgets import QCheckBox, QMessageBox, QSpinBox

from opencae.model.entities.optimization import SymmetryType, TopologySymmetry
from opencae.model.selection import SelectableKind
from opencae.ui.core.named_entity_dialog import NamedEntityDialog
from opencae.ui.core.widgets import ChevronComboBox, PickReference


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
            width=540,
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
        self.enabled = QCheckBox("Enabled")
        self.enabled.setChecked(self.value.enabled)

        self.form.addRow("Type", self.kind)
        self.form.addRow("Reference", self.reference)
        self.form.addRow("Occurrences", self.occurrences)
        self.form.addRow("", self.enabled)
        self.finished.connect(lambda _code: self._cleanup())
        self._kind_changed()
        self.finish()

    def result(self):
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
        allowed = self._allowed_kinds()
        self.reference.allowed = tuple(allowed)
        current = self.reference.reference()
        if current and current.get("kind") not in self._allowed_reference_names():
            self.reference.set_reference(None)

    def _allowed_kinds(self):
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
        if self.kind.currentData() == SymmetryType.PLANAR.value:
            return {"face", "datum_plane"}
        return {"edge", "datum_vector"}

    def _request_pick(self, _allowed, done, finished):
        if self._pick_reference is None:
            finished()
            return
        self._pick_reference(
            SymmetryType(self.kind.currentData()),
            done,
            finished,
        )

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
