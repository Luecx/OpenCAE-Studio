"""Regression checks for the continuous lower-workspace visual surface."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_lower_workspace_status_tabs_and_contents_share_one_surface_color():
    misc = (ROOT / "opencae/ui/core/styles/misc.py").read_text(encoding="utf-8")
    docks = (ROOT / "opencae/ui/core/styles/docks.py").read_text(encoding="utf-8")
    output = (ROOT / "opencae/ui/docks/output_dock.py").read_text(encoding="utf-8")
    layout = (ROOT / "opencae/app/window_layout.py").read_text(encoding="utf-8")
    controller = (ROOT / "opencae/ui/docks/workspace_controller.py").read_text(encoding="utf-8")

    assert 'QToolButton[workspaceStatusTab="true"]' in misc
    assert "background: {p['panel']};" in misc
    assert "border-top: 2px solid {p['accent']}" in misc
    assert "QWidget#WorkspaceSurface" in docks
    assert "QFrame#TimeManagerSidebar" in docks
    assert "background: transparent" in docks
    assert 'self.surface.setObjectName("WorkspaceSurface")' in output
    assert 'surface_layout.setContentsMargins(0, 0, 0, 0)' in output
    assert "QStackedWidget" in output
    assert "tabifyDockWidget" not in layout
    assert "window.workspace_dock" in layout
    assert "self.dock.set_page(name)" in controller
    assert "removeDockWidget" not in controller
    assert "addDockWidget" not in controller
    assert "tabifiedDockWidgets" not in controller
