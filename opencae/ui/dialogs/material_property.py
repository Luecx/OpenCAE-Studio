"""Provides the focused editor for one material-behavior definition."""

from PyQt6.QtWidgets import QDialog, QStackedWidget, QVBoxLayout, QWidget

from opencae.model.entities.resources.material_behaviors import (
    DensityBehavior,
    IsotropicElasticity,
    IsotropicPlasticity,
    IsotropicThermalExpansion,
    NeoHookeElasticity,
)
from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.templates import (
    NumericUnitInput,
    SectionHeading,
    dialog_buttons,
    field_block,
    field_row,
    scaffold_dialog,
)

_BY_CATEGORY = {
    "Elasticity": ("Isotropic elasticity", "Neo-Hooke"),
    "Density": ("Constant density",),
    "Plasticity": ("Bilinear isotropic hardening",),
    "Thermal expansion": ("Isotropic expansion",),
}

_PROPERTY_SPECS = {
    "Isotropic elasticity": (
        ("Young's modulus", 210000.0, "pressure"),
        ("Poisson ratio", 0.3, None),
    ),
    "Neo-Hooke": (("C10", 1.0, "pressure"), ("D1", 0.0, "compliance")),
    "Constant density": (("Density", 0.0, "density"),),
    "Isotropic expansion": (
        ("Expansion coefficient", 0.0, "thermal_expansion"),
        ("Reference temperature", 20.0, "temperature"),
    ),
    "Bilinear isotropic hardening": (
        ("Yield stress", 250.0, "pressure"),
        ("Tangent modulus", 0.0, "pressure"),
    ),
}


class MaterialPropertyDialog(QDialog):
    """Edit one material behavior using the same field hierarchy as MaterialDialog."""

    def __init__(self, behavior=None, parent=None, category=None, units=None):
        """Build the behavior-type selector and its unit-aware property values."""
        super().__init__(parent)
        self.behavior = behavior
        self.units = units or getattr(getattr(parent, "controllers", None), "units", None)
        self.category = category or getattr(behavior, "category", "Elasticity")
        self.types = _BY_CATEGORY[self.category]

        scaffold = scaffold_dialog(self, self.category, width=620)
        self.kind = ChevronComboBox()
        self.kind.addItems(self.types)
        self.kind.setCurrentText(getattr(behavior, "behavior_type", self.types[0]))
        scaffold.form.addRow("Definition", self.kind)

        scaffold.root.addWidget(SectionHeading("Property Values"))
        self.stack = QStackedWidget()
        scaffold.root.addWidget(self.stack)
        self._pages = {}
        for kind in self.types:
            self._add_page(kind)

        self.kind.currentTextChanged.connect(
            lambda text: self.stack.setCurrentIndex(self.types.index(text))
        )
        self.stack.setCurrentIndex(self.types.index(self.kind.currentText()))
        self._load()

        buttons = dialog_buttons()
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        scaffold.root.addWidget(buttons)

    def _add_page(self, kind):
        """Create one behavior page with paired unit-aware scalar fields."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        editors = []
        blocks = []
        for text, default, quantity in _PROPERTY_SPECS[kind]:
            unit = (
                self.units.suffix(quantity)
                if self.units is not None and quantity
                else ""
            )
            editor = NumericUnitInput(
                default,
                unit,
                minimum=-1e30,
                maximum=1e30,
                decimals=8,
            )
            editors.append(editor)
            blocks.append(field_block(text, editor))

        # Material properties naturally occur in pairs. Keeping both values on
        # one row mirrors the main Material dialog without introducing a table.
        for index in range(0, len(blocks), 2):
            pair = blocks[index:index + 2]
            layout.addWidget(field_row(*pair) if len(pair) == 2 else pair[0])
        layout.addStretch(1)

        self._pages[kind] = editors
        self.stack.addWidget(page)

    def _load(self):
        """Populate the active page from the existing behavior when editing."""
        behavior = self.behavior
        values = []
        if isinstance(behavior, IsotropicElasticity):
            values = [behavior.youngs_modulus, behavior.poisson_ratio]
        elif isinstance(behavior, NeoHookeElasticity):
            values = [behavior.c10, behavior.d1]
        elif isinstance(behavior, DensityBehavior):
            values = [behavior.value]
        elif isinstance(behavior, IsotropicThermalExpansion):
            values = [behavior.coefficient, behavior.reference_temperature]
        elif isinstance(behavior, IsotropicPlasticity):
            values = [behavior.yield_stress, behavior.tangent_modulus]
        for editor, value in zip(self._pages[self.kind.currentText()], values):
            editor.setValue(value)

    def behavior_value(self):
        """Return the material-behavior entity represented by the current page."""
        kind = self.kind.currentText()
        values = [editor.value() for editor in self._pages[kind]]
        return {
            "Isotropic elasticity": lambda: IsotropicElasticity(
                youngs_modulus=values[0], poisson_ratio=values[1]
            ),
            "Neo-Hooke": lambda: NeoHookeElasticity(c10=values[0], d1=values[1]),
            "Constant density": lambda: DensityBehavior(value=values[0]),
            "Isotropic expansion": lambda: IsotropicThermalExpansion(
                coefficient=values[0], reference_temperature=values[1]
            ),
            "Bilinear isotropic hardening": lambda: IsotropicPlasticity(
                yield_stress=values[0], tangent_modulus=values[1]
            ),
        }[kind]()
