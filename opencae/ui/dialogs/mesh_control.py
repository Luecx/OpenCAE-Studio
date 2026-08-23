"""Provides the mesh topology/technique control editor for selected regions."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLineEdit

from opencae.model.selection import RegionDefinition
from opencae.ui.core.widgets import ChevronComboBox, CompactRegionSelector
from opencae.ui.templates import (
    FieldLabel,
    SectionHeading,
    apply_primary_control_height,
    dialog_buttons,
    dialog_layout,
    field_block,
    field_row,
)


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
        """Build the mesh-control definition with scope-aware viewport picking."""
        super().__init__(parent)
        self.setWindowTitle("Mesh Control")
        self.setMinimumSize(720, 500)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        root = dialog_layout(self)

        self.name = QLineEdit(control.name if control else "Mesh Control-1")
        apply_primary_control_height(self.name)
        self.scope = _combo(("Edge", "Face", "Cell"), control.scope if control else "Cell")
        root.addWidget(
            field_row(
                field_block("Name", self.name),
                field_block("Scope", self.scope),
            )
        )

        root.addWidget(SectionHeading("Mesh Control Definition"))
        self._pick_callback = pick_callback
        self.target = CompactRegionSelector(
            project,
            definition or getattr(control, "target", RegionDefinition()),
            options,
            self._pick,
            parent=self,
        )
        root.addWidget(field_block("Target region", self.target))
        root.addWidget(FieldLabel("Leave the target empty to address all entities of the selected scope."))

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
            field_row(
                field_block("Preferred topology", self.topology),
                field_block("Technique", self.technique),
            )
        )
        root.addStretch(1)

        buttons = dialog_buttons()
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _pick(self, owner, done, finished):
        """Delegate picking using the currently selected geometry scope."""
        if self._pick_callback:
            return self._pick_callback(self.scope.currentText(), owner, done, finished)
        return None

    def values(self):
        """Return the current mesh-control constructor values."""
        return {
            "name": self.name.text().strip(),
            "scope": self.scope.currentText(),
            "target": self.target.definition(),
            "topology": self.topology.currentText(),
            "technique": self.technique.currentText(),
        }


def _combo(values, current):
    """Build one canonical mesh-control combo."""
    control = ChevronComboBox()
    control.setMinimumWidth(0)
    control.addItems(values)
    control.setCurrentText(current)
    apply_primary_control_height(control)
    return control
