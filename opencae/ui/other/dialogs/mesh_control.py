"""Provides the mesh topology/technique control editor for selected regions."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog

from opencae.model.selection import RegionDefinition
from opencae.ui.components import CompactRegionSelector
from opencae.ui.primitives.inputs import InputFormText
from opencae.ui.primitives.selects import SelectForm
from opencae.ui.primitives.labels import LabelForm, LabelSection
from opencae.ui.components.dialogs import dialog_buttons
from opencae.ui.components.layouts import dialog_layout
from opencae.ui.components.form_field import FormField
from opencae.ui.components.field_row import FieldRow

class MeshControlDialog(QDialog):
    """Edit mesh scope, target, preferred topology and meshing technique."""

    def __init__(
        self,
        project,
        options=(),
        definition=None,
        pick_callback=None,
        control=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Mesh Control")
        self.setMinimumSize(720, 500)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        root = dialog_layout(self)

        self.name = InputFormText(control.name if control else "Mesh Control-1")
        self.scope = _combo(("Edge", "Face", "Cell"), control.scope if control else "Cell")
        root.addWidget(
            FieldRow(
                FormField("Name", self.name),
                FormField("Scope", self.scope),
            )
        )

        root.addWidget(LabelSection("Mesh Control Definition"))
        self._pick_callback = pick_callback
        self.target = CompactRegionSelector(
            project,
            definition or getattr(control, "target", RegionDefinition()),
            options,
            self._pick,
            parent=self,
        )
        root.addWidget(FormField("Target region", self.target))
        root.addWidget(LabelForm("Leave the target empty to address all entities of the selected scope."))

        self.topology = _combo(
            (
                "Line",
                "Triangular",
                "Quadrilateral",
                "Tetrahedral",
                "Pyramidal",
                "Pentahedral",
                "Hexahedral",
            ),
            control.topology if control else "Tetrahedral",
        )
        self.technique = _combo(
            ("Free", "Structured", "Transfinite", "Recombine"),
            control.technique if control else "Free",
        )
        root.addWidget(
            FieldRow(
                FormField("Preferred topology", self.topology),
                FormField("Technique", self.technique),
            )
        )
        root.addStretch(1)

        buttons = dialog_buttons()
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _pick(self, owner, done, finished):
        if self._pick_callback:
            return self._pick_callback(self.scope.currentText(), owner, done, finished)
        return None

    def values(self):
        return {
            "name": self.name.text().strip(),
            "scope": self.scope.currentText(),
            "target": self.target.definition(),
            "topology": self.topology.currentText(),
            "technique": self.technique.currentText(),
        }


def _combo(values, current):
    control = SelectForm()
    control.addItems(values)
    control.setCurrentText(current)
    return control
