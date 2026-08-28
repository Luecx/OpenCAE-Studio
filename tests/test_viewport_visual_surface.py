"""Regressions for viewport contrast, gradient, and lightweight horizon styling."""

from pathlib import Path

from opencae.ui.core.theme import PALETTE


ROOT = Path(__file__).resolve().parents[1]


def test_viewport_palette_uses_lighter_gradient_and_visible_mesh_lines():
    assert PALETTE["viewport_top"] != PALETTE["viewport_bottom"]
    assert PALETTE["viewport"] != "#101319"
    assert PALETTE["mesh_lines"] not in {"#182129", PALETTE["viewport_top"]}
    assert PALETTE["viewport_horizon"] not in {
        PALETTE["viewport_top"],
        PALETTE["viewport_bottom"],
    }


def test_safe_interactor_promotes_viewport_token_to_gradient():
    source = (ROOT / "opencae/ui/viewport/safe_qt_interactor.py").read_text(
        encoding="utf-8"
    )
    assert 'color == PALETTE["viewport"]' in source
    assert 'color = PALETTE["viewport_bottom"]' in source
    assert 'top = PALETTE["viewport_top"]' in source


def test_viewport_canvas_keeps_one_subtle_camera_independent_horizon():
    source = (ROOT / "opencae/ui/viewport/viewport_canvas.py").read_text(
        encoding="utf-8"
    )
    assert 'self.horizon.setFixedHeight(1)' in source
    assert 'PALETTE[\'viewport_horizon\']' in source
    assert 'round(render_height * 0.62)' in source
    assert "WA_TransparentForMouseEvents" in source


def test_result_mesh_lines_use_theme_contrast_color():
    source = (ROOT / "opencae/ui/viewport/result_visualization.py").read_text(
        encoding="utf-8"
    )
    assert 'color=PALETTE["mesh_lines"]' in source
    assert 'edge_color=PALETTE["mesh_lines"]' in source
    assert '#182129' not in source


def test_view_cube_opaque_fill_matches_gradient_top_near_its_anchor():
    source = (ROOT / "opencae/ui/viewport/view_cube.py").read_text(
        encoding="utf-8"
    )
    assert 'QColor(PALETTE["viewport_top"])' in source
