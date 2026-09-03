"""Regression coverage for centralized UI and viewport color schemes."""

from pathlib import Path

from opencae.ui.core.theme import (
    PALETTE,
    color_scheme_label,
    color_scheme_names,
    current_color_scheme,
    normalize_color_scheme,
    palette_for,
    set_color_scheme,
    stylesheet,
)


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_builtin_schemes_share_one_semantic_token_contract():
    names = color_scheme_names()
    assert names == ("dark", "light", "pycharm-gray")
    expected = set(palette_for(names[0]))
    assert {
        "window",
        "panel",
        "input",
        "text",
        "muted",
        "accent",
        "viewport",
        "cad_face",
        "cad_edge",
        "mesh_surface",
        "mesh_lines",
        "selection_3d",
        "overlay_bg",
        "overlay_text",
        "axis_x",
        "axis_y",
        "axis_z",
    } <= expected
    for name in names[1:]:
        assert set(palette_for(name)) == expected


def test_schemes_are_visually_distinct_and_have_stable_labels():
    dark = palette_for("dark")
    light = palette_for("light")
    gray = palette_for("pycharm-gray")

    assert color_scheme_label("dark") == "OpenCAE Dark"
    assert color_scheme_label("light") == "OpenCAE Light"
    assert color_scheme_label("pycharm") == "PyCharm Gray"
    assert normalize_color_scheme("grey") == "pycharm-gray"
    assert normalize_color_scheme("does-not-exist") == "dark"

    assert dark["window"] != light["window"] != gray["window"]
    assert dark["viewport"] != light["viewport"] != gray["viewport"]
    assert light["window"].lower() in stylesheet("light").lower()
    assert gray["panel"].lower() in stylesheet("pycharm-gray").lower()


def test_switching_scheme_mutates_shared_palette_in_place():
    original_scheme = current_color_scheme()
    palette_identity = id(PALETTE)
    try:
        selected = set_color_scheme("light")
        assert selected == "light"
        assert current_color_scheme() == "light"
        assert id(PALETTE) == palette_identity
        assert PALETTE == palette_for("light")

        selected = set_color_scheme("pycharm")
        assert selected == "pycharm-gray"
        assert id(PALETTE) == palette_identity
        assert PALETTE == palette_for("pycharm-gray")
    finally:
        set_color_scheme(original_scheme)


def test_startup_applies_persisted_scheme_before_widgets_are_created():
    source = _source("opencae/app/application.py")
    assert 'appearance.value("appearance/color_scheme"' in source
    assert source.index("apply_color_scheme(") < source.index("startup = StartupWindow()")


def test_view_menu_exposes_and_persists_live_color_scheme_switching():
    source = _source("opencae/ui/menus/view_menu.py")
    registry = _source("opencae/ui/actions/registry.py")

    assert 'menu.addMenu("Color Scheme")' in source
    assert 'settings.set_value("appearance/color_scheme", selected)' in source
    assert "apply_color_scheme(app, scheme)" in source
    assert "refresh_theme()" in source
    assert "viewport.request_refresh()" in source
    assert "def refresh_icons(self)" in registry


def test_key_viewport_chrome_uses_semantic_palette_tokens():
    files = {
        "opencae/ui/viewport/pyvista_geometry.py": (
            'PALETTE["cad_face"]',
            'PALETTE["cad_edge"]',
            'PALETTE["selection_3d"]',
        ),
        "opencae/ui/viewport/pyvista_mesh.py": ('PALETTE["mesh_lines"]',),
        "opencae/ui/viewport/surface_shading.py": ('PALETTE["mesh_surface"]',),
        "opencae/ui/viewport/datum_overlay.py": (
            'PALETTE["datum"]',
            'PALETTE["datum_vector"]',
            'PALETTE["datum_plane"]',
        ),
        "opencae/ui/viewport/reference_point_overlay.py": (
            'PALETTE["reference_point"]',
            'PALETTE["overlay_text"]',
        ),
        "opencae/ui/viewport/result_query_state.py": ('PALETTE["query_marker"]',),
        "opencae/ui/viewport/view_cube.py": (
            'PALETTE["viewport"]',
            'PALETTE["cad_face"]',
            'PALETTE["viewport_text"]',
        ),
    }
    for path, tokens in files.items():
        source = _source(path)
        for token in tokens:
            assert token in source, (path, token)


def test_previous_dark_only_chrome_literals_are_removed_from_migrated_components():
    checks = {
        "opencae/ui/core/styles/menus.py": "#66717c",
        "opencae/ui/core/styles/materials.py": "#173526",
        "opencae/ui/core/styles/fields.py": "#53606d",
        "opencae/ui/viewport/pyvista_mesh.py": "#182129",
        "opencae/ui/viewport/field_visualization.py": "#10161c",
        "opencae/ui/viewport/reference_point_overlay.py": "#62d6a6",
        "opencae/ui/viewport/result_query_state.py": "#f2b84b",
    }
    for path, literal in checks.items():
        assert literal not in _source(path), (path, literal)
