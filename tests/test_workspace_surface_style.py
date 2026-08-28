"""Regression checks for the continuous lower-workspace visual surface."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_lower_workspace_tab_strip_and_contents_share_one_surface_color():
    tabs = (ROOT / "opencae/ui/core/styles/tabs.py").read_text(encoding="utf-8")
    docks = (ROOT / "opencae/ui/core/styles/docks.py").read_text(encoding="utf-8")
    output = (ROOT / "opencae/ui/docks/output_dock.py").read_text(encoding="utf-8")

    assert "QTabBar {" in tabs
    assert "background: {p['panel']};" in tabs
    assert "border-top:" not in tabs
    assert 'QWidget[workspaceSurface="true"]' in docks
    assert "background: {p['panel']};" in docks
    assert 'widget.setProperty("workspaceSurface", True)' in output
    assert "QFrame#TimeManagerSidebar { background: transparent; border: none; }" in output
