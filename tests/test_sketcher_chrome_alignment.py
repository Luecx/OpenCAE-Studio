"""Keep Sketcher ribbon and splitter chrome aligned with the main window."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_sketch_ribbon_uses_main_ribbon_panel_surface():
    sketch = _source("opencae/ui/sketcher/constraint_dialog.py")
    main_ribbon = _source("opencae/ui/ribbon/ribbon.py")

    assert "Qt.WidgetAttribute.WA_StyledBackground" in sketch
    assert "PALETTE['panel']" in sketch
    assert "PALETTE['border']" in sketch
    assert "PALETTE['panel']" in main_ribbon
    assert "PALETTE['border']" in main_ribbon


def test_sketch_workspace_splitter_matches_main_window_separator_width():
    sketch = _source("opencae/ui/sketcher/constraint_dialog.py")
    misc = _source("opencae/ui/core/styles/misc.py")

    assert "_MAIN_SEPARATOR_WIDTH = 3" in sketch
    assert "splitter.setHandleWidth(_MAIN_SEPARATOR_WIDTH)" in sketch
    assert "QMainWindow::separator {{ width: 3px;" in misc
