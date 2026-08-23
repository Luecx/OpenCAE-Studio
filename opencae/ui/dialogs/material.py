"""Provides the redesigned Create/Edit Material dialog with inline behaviors."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from opencae.ui.core.apply_dialog import ApplyDialog
from opencae.ui.templates import dialog_buttons
from .material_behavior_card import MaterialBehaviorCard
from .material_behavior_specs import CATEGORIES


class MaterialDialog(ApplyDialog):
    """Create or edit a Material using compact inline behavior cards."""

    def __init__(
        self,
        material=None,
        existing_names=(),
        parent=None,
        default_name="Material-1",
        units=None,
    ):
        super().__init__(parent)
        self.material = material
        self.units = units
        self.existing_names = {name.casefold() for name in existing_names}
        self.cards: dict[str, MaterialBehaviorCard] = {}

        self.setWindowTitle("Edit Material" if material else "Create Material")
        self.setMinimumSize(760, 600)
        self.resize(840, 690)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(14)

        name_label = QLabel("Name")
        name_label.setObjectName("MaterialTopLabel")
        root.addWidget(name_label)

        self.name = QLineEdit(material.name if material else default_name)
        root.addWidget(self.name)

        definitions = QLabel("Material Definitions")
        definitions.setObjectName("MaterialSectionTitle")
        root.addWidget(definitions)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setObjectName("MaterialDefinitionsScroll")

        content = QWidget()
        content.setObjectName("MaterialDefinitionsContent")
        cards_layout = QVBoxLayout(content)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(10)

        existing = {
            behavior.category: behavior
            for behavior in tuple(getattr(material, "behaviors", ()))
        }
        for category in CATEGORIES:
            card = MaterialBehaviorCard(
                category,
                existing.get(category),
                self.units,
                content,
            )
            cards_layout.addWidget(card)
            self.cards[category] = card
        cards_layout.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        buttons = dialog_buttons(include_apply=True)
        self.bind_buttons(buttons, True)
        root.addWidget(buttons)

    def validate(self) -> bool:
        """Reject empty or duplicate material names before committing."""
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid material", "Enter a material name.")
            return False
        duplicate = name.casefold() in self.existing_names
        unchanged = self.material is not None and name.casefold() == self.material.name.casefold()
        if duplicate and not unchanged:
            QMessageBox.warning(
                self,
                "Duplicate name",
                f"A material named '{name}' already exists.",
            )
            return False
        return True

    def values(self) -> dict:
        """Return Material constructor values from the current inline editors."""
        behaviors = []
        for category in CATEGORIES:
            behavior = self.cards[category].behavior_value()
            if behavior is not None:
                behaviors.append(behavior)
        return {
            "name": self.name.text().strip(),
            "behaviors": behaviors,
            "fields": [],
            "properties": dict(getattr(self.material, "properties", {})),
            "density": 0.0,
            "youngs_modulus": 0.0,
            "poisson_ratio": 0.0,
        }

    def prepare_new(self, default_name, existing_names) -> None:
        """Reset the reusable dialog after Apply creates a new Material."""
        self.material = None
        self.existing_names = {name.casefold() for name in existing_names}
        self.name.setText(default_name)
        for card in self.cards.values():
            card.set_behavior(None)
