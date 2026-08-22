from PyQt6.QtWidgets import QDialog, QDoubleSpinBox, QFormLayout, QLabel, QStackedWidget, QVBoxLayout, QWidget

from opencae.model.entities.resources.material_behaviors import DensityBehavior, IsotropicElasticity, IsotropicPlasticity, IsotropicThermalExpansion, NeoHookeElasticity
from opencae.ui.core.controls import dialog_buttons
from opencae.ui.core.unit_context import unit_system_for
from opencae.ui.core.widgets import ChevronComboBox

_BY_CATEGORY = {
    "Elasticity": ("Isotropic elasticity", "Neo-Hooke"),
    "Density": ("Constant density",),
    "Plasticity": ("Bilinear isotropic hardening",),
    "Thermal expansion": ("Isotropic expansion",),
}


class MaterialPropertyDialog(QDialog):
    def __init__(self, behavior=None, parent=None, category=None):
        super().__init__(parent); self.behavior = behavior; self.category = category or getattr(behavior, "category", "Elasticity"); self.unit_system = unit_system_for(self)
        self.types = _BY_CATEGORY[self.category]; self.setWindowTitle(self.category); self.setMinimumWidth(520)
        root = QVBoxLayout(self); root.setContentsMargins(18, 16, 18, 14); title = QLabel(self.category); title.setObjectName("PanelTitle"); root.addWidget(title)
        form = QFormLayout(); self.kind = ChevronComboBox(); self.kind.addItems(self.types); self.kind.setCurrentText(getattr(behavior, "behavior_type", self.types[0])); form.addRow("Definition", self.kind); root.addLayout(form)
        self.stack = QStackedWidget(); root.addWidget(self.stack); self._pages = {}
        for kind in self.types: self._add_page(kind)
        self.kind.currentTextChanged.connect(lambda text: self.stack.setCurrentIndex(self.types.index(text))); self.stack.setCurrentIndex(self.types.index(self.kind.currentText())); self._load()
        buttons = dialog_buttons(); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); root.addWidget(buttons)

    def _add_page(self, kind):
        specs = {
            "Isotropic elasticity": (("Young's modulus", 210000.0, "pressure"), ("Poisson ratio", 0.3, None)),
            "Neo-Hooke": (("C10", 1.0, "pressure"), ("D1", 0.0, "compliance")),
            "Constant density": (("Density", 0.0, "density"),),
            "Isotropic expansion": (("Expansion coefficient", 0.0, "thermal_expansion"), ("Reference temperature", 20.0, "temperature")),
            "Bilinear isotropic hardening": (("Yield stress", 250.0, "pressure"), ("Tangent modulus", 0.0, "pressure")),
        }[kind]
        page = QWidget(); form = QFormLayout(page); editors = []
        for label, default, quantity in specs:
            editor = QDoubleSpinBox(); editor.setRange(-1e30, 1e30); editor.setDecimals(8); editor.setValue(default)
            if quantity: editor.setSuffix(f" {self.unit_system.symbol(quantity)}")
            form.addRow(label, editor); editors.append(editor)
        self._pages[kind] = editors; self.stack.addWidget(page)

    def _load(self):
        b = self.behavior; values = []
        if isinstance(b, IsotropicElasticity): values = [b.youngs_modulus, b.poisson_ratio]
        elif isinstance(b, NeoHookeElasticity): values = [b.c10, b.d1]
        elif isinstance(b, DensityBehavior): values = [b.value]
        elif isinstance(b, IsotropicThermalExpansion): values = [b.coefficient, b.reference_temperature]
        elif isinstance(b, IsotropicPlasticity): values = [b.yield_stress, b.tangent_modulus]
        for editor, value in zip(self._pages[self.kind.currentText()], values): editor.setValue(value)

    def behavior_value(self):
        kind = self.kind.currentText(); values = [editor.value() for editor in self._pages[kind]]
        return {"Isotropic elasticity": lambda: IsotropicElasticity(youngs_modulus=values[0], poisson_ratio=values[1]), "Neo-Hooke": lambda: NeoHookeElasticity(c10=values[0], d1=values[1]), "Constant density": lambda: DensityBehavior(value=values[0]), "Isotropic expansion": lambda: IsotropicThermalExpansion(coefficient=values[0], reference_temperature=values[1]), "Bilinear isotropic hardening": lambda: IsotropicPlasticity(yield_stress=values[0], tangent_modulus=values[1])}[kind]()
