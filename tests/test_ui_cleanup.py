from pathlib import Path

from opencae.units import UnitSystem


ROOT = Path(__file__).resolve().parents[1]


def test_profile_units_come_from_active_unit_system():
    source = (ROOT / "opencae/ui/dialogs/profile.py").read_text(encoding="utf-8")
    assert '"mm²"' not in source
    assert '"mm⁴"' not in source
    assert 'self.unit_system.symbol("length")' in source
    assert 'self.unit_system.symbol(quantity)' in source


def test_unit_system_can_format_profile_quantities():
    system = UnitSystem("SI", length="m", force="N", time="s", temperature="°C")
    assert system.symbol("length") == "m"
    assert system.symbol("area") == "m²"
    assert system.symbol("section_inertia") == "m⁴"


def test_spinbox_stepper_buttons_are_hidden_globally():
    source = (ROOT / "opencae/ui/core/styles/fields.py").read_text(encoding="utf-8")
    assert "QSpinBox::up-button" in source
    assert "QSpinBox::down-button" in source
    assert "QDoubleSpinBox::up-button" in source
    assert "QDoubleSpinBox::down-button" in source


def test_clear_and_suppress_use_clean_accent_x():
    factory = (ROOT / "opencae/ui/core/icons/factory.py").read_text(encoding="utf-8")
    actions = (ROOT / "opencae/ui/actions/catalog/part_actions.py").read_text(encoding="utf-8")
    assert "if kind == IconKind.CLEAR" in factory
    assert 'PALETTE["accent"]' in factory
    assert 'ActionSpec(A.CLEAR_MESH, "Clear Mesh", I.CLEAR' in actions
    assert 'ActionSpec(A.SUPPRESS_FEATURE, "Suppress / Resume", I.CLEAR' in actions


def test_ribbon_context_status_row_is_removed():
    source = (ROOT / "opencae/ui/ribbon/ribbon.py").read_text(encoding="utf-8")
    assert "_context_label" not in source
    assert "CONTEXT_BAR_HEIGHT" not in source
    assert "No active part" not in source
    assert "layout.addWidget(self.stage_bar)" in source
    assert "layout.addWidget(self.stack)" in source
