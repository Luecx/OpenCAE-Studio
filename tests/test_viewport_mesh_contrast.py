"""Regression coverage for mesh-line visibility and meshability face contrast."""

from colorsys import rgb_to_hsv
from pathlib import Path

from opencae.ui.core.theme import color_scheme_names, palette_for


ROOT = Path(__file__).resolve().parents[1]


def _rgb(value):
    text = str(value).lstrip("#")
    return tuple(int(text[index:index + 2], 16) / 255.0 for index in (0, 2, 4))


def _luminance(value):
    channels = []
    for channel in _rgb(value):
        channels.append(
            channel / 12.92
            if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast(first, second):
    low, high = sorted((_luminance(first), _luminance(second)))
    return (high + 0.05) / (low + 0.05)


def test_mesh_lines_keep_strong_contrast_against_neutral_mesh_surface():
    for name in color_scheme_names():
        palette = palette_for(name)
        assert _contrast(palette["mesh_lines"], palette["mesh_surface"]) >= 4.5


def test_irregular_meshability_color_remains_visibly_purple():
    for name in color_scheme_names():
        palette = palette_for(name)
        red, green, blue = _rgb(palette["meshability_irregular"])
        _hue, saturation, _value = rgb_to_hsv(red, green, blue)
        assert saturation >= 0.35
        assert blue > green
        assert red > green


def test_results_are_rebuilt_when_the_color_scheme_changes():
    source = (ROOT / "opencae/ui/menus/view_menu.py").read_text(encoding="utf-8")
    scene = (ROOT / "opencae/ui/viewport/solution_scene.py").read_text(encoding="utf-8")
    mesh = (ROOT / "opencae/ui/viewport/pyvista_mesh.py").read_text(encoding="utf-8")

    assert "page._emit()" in source
    assert 'PALETTE["mesh_lines"]' in scene
    assert "1.35" in scene
    assert 'PALETTE["mesh_lines"]' in mesh
    assert "line_width=1.35" in mesh
