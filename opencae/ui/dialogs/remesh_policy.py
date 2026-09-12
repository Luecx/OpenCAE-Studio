"""Explicit remesh-decision dialog for mixed-origin meshes."""

from PyQt6.QtWidgets import QCheckBox, QDialog

from opencae.model.mesh import (
    RemeshAssociationMode,
    RemeshPolicy,
    RemeshReplacementMode,
)
from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.templates import (
    SectionHeading,
    apply_primary_control_height,
    dialog_buttons,
    dialog_layout,
    field_block,
)


class RemeshPolicyDialog(QDialog):
    """Ask how authored/imported FE entities survive CAD remeshing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Remesh Existing Mesh")
        self.setMinimumWidth(620)
        root = dialog_layout(self)
        root.addWidget(SectionHeading("Existing manual/imported mesh data"))

        self.replacement = ChevronComboBox()
        self.replacement.addItem(
            "Replace the entire mesh",
            RemeshReplacementMode.REPLACE_ALL,
        )
        self.replacement.addItem(
            "Replace generated entities; preserve authored/imported entities",
            RemeshReplacementMode.REPLACE_GENERATED,
        )
        self.replacement.setCurrentIndex(1)
        apply_primary_control_height(self.replacement)
        root.addWidget(field_block("Replacement rule", self.replacement))

        self.discard_associations = QCheckBox(
            "Discard CAD associations after remeshing"
        )
        self.convert_to_authored = QCheckBox(
            "Convert the final mesh to a pure authored mesh"
        )
        root.addWidget(self.discard_associations)
        root.addWidget(self.convert_to_authored)
        root.addStretch(1)

        buttons = dialog_buttons()
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def values(self) -> RemeshPolicy:
        return RemeshPolicy(
            replacement=self.replacement.currentData(),
            associations=(
                RemeshAssociationMode.DISCARD
                if self.discard_associations.isChecked()
                else RemeshAssociationMode.REBUILD
            ),
            convert_to_authored=self.convert_to_authored.isChecked(),
        )
