"""Regressions for viewport contrast and flat render-surface styling."""

from pathlib import Path

from opencae.ui.core.theme import PALETTE


ROOT = Path(__file__).resolve().parents[1]


def test_viewport_palette_uses_lighter_solid_surface_and_visible_mesh_lines():
    assert PALETTE["viewport"] != "#101319"
    assert "viewport_top" not in PALETTE
    assert "viewport_bottom" not in PALETTE
    assert "viewport_horizon" not in PALETTE
    assert PALETTE["mesh_lines"] not in {"#182129", PALETTE["viewport"]}


def test_safe_interactor_no_longer_promotes_viewport_to_gradient():
    source = (ROOT / "opencae/ui/viewport/safe_qt_interactor.py").read_text(
        encoding="utf-8"
    )
    assert "def set_background" not in source
    assert "viewport_top" not in source
    assert "viewport_bottom" not in source


def test_viewport_canvas_has_no_artificial_horizon_overlay():
    source = (ROOT / "opencae/ui/viewport/viewport_canvas.py").read_text(
        encoding="utf-8"
    )
    assert "ViewportHorizon" not in source
    assert "self.horizon" not in source
    assert "viewport_horizon" not in source


def test_result_mesh_lines_use_theme_contrast_color():
    source = (ROOT / "opencae/ui/viewport/result_visualization.py").read_text(
        encoding="utf-8"
    )
    topology_source = (ROOT / "opencae/ui/viewport/topology_presentation.py").read_text(
        encoding="utf-8"
    )
    assert 'color=PALETTE["mesh_lines"]' in source
    assert 'edge_color=PALETTE["mesh_lines"]' in source
    assert 'color=PALETTE["mesh_lines"]' in topology_source
    assert "#182129" not in source


def test_view_cube_opaque_fill_matches_exact_viewport_surface():
    source = (ROOT / "opencae/ui/viewport/view_cube.py").read_text(
        encoding="utf-8"
    )
    assert 'QColor(PALETTE["viewport"])' in source
    assert "viewport_top" not in source
