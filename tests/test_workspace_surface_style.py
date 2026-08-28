"""Regression checks for the continuous lower-workspace visual surface."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_lower_workspace_tab_strip_and_contents_share_one_surface_color():
    tabs = (ROOT / "opencae/ui/core/styles/tabs.py").read_text(encoding="utf-8")
    docks = (ROOT / "opencae/ui/core/styles/docks.py").read_text(encoding="utf-8")
    output = (ROOT / "opencae/ui/docks/output_dock.py").read_text(encoding="utf-8")
    layout = (ROOT / "opencae/app/window_layout.py").read_text(encoding="utf-8")

    assert "QTabBar#WorkspaceTabBar" in tabs
    assert "qproperty-drawBase: false" in tabs
    assert "background: {p['panel']};" in tabs
    assert "QWidget#WorkspaceSurface" in docks
    assert "QFrame#TimeManagerSidebar" in docks
    assert "background: transparent" in docks
    assert 'self.surface.setObjectName("WorkspaceSurface")' in output
    assert 'surface_layout.setContentsMargins(0, 0, 0, 0)' in output
    assert 'tab_bar.setObjectName("WorkspaceTabBar")' in layout
    assert "tab_bar.setDrawBase(False)" in layout
    assert "tab_bar.setExpanding(False)" in layout
