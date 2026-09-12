"""Architecture contracts for reusable viewport-toolbar controls."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    """Read one repository source file for a lightweight architecture check."""
    return (ROOT / path).read_text(encoding="utf-8")


def test_selection_toolbar_uses_one_canonical_button_class():
    """Keep selection, display, projection, and fit controls geometrically aligned."""
    source = _source("opencae/ui/viewport/selection_toolbar.py")
    assert "ViewportToolButton(" in source
    assert "QToolButton(" not in source
    assert "ProjectionToggle" not in source


def test_viewport_tool_style_has_one_shared_selector():
    """Prevent projection-specific padding from diverging again."""
    source = _source("opencae/ui/core/styles/buttons.py")
    assert 'QToolButton[viewportTool="true"]' in source
    assert "QToolButton#ProjectionToggle" not in source
