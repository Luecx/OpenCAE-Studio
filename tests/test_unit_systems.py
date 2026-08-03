from opencae.units import UnitSystem, default_systems


def test_mm_n_system_recognizes_engineering_units():
    system = default_systems()[0]
    assert system.symbol("pressure") == "MPa"
    assert system.symbol("mass") == "t"
    assert system.symbol("density") == "t/mm³"
    assert system.symbol("section_inertia") == "mm⁴"


def test_conversion_to_si_system():
    source, target = default_systems()[:2]
    assert source.conversion_to(target, "length") == (1e-3, 0.0)
    assert source.conversion_to(target, "pressure") == (1e6, 0.0)
    assert source.conversion_to(target, "temperature") == (1.0, 273.15)


def test_custom_system_roundtrip():
    system = UnitSystem("Custom", "cm", "kN", "ms", "°F")
    assert UnitSystem.from_dict(system.to_dict()) == system
