"""Source-level regressions for flat ribbon and Browser tab surfaces."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_results_ribbon_uses_flat_surface_with_subtle_active_toggle_lift():
    group_source = (ROOT / "opencae/ui/ribbon/result_group.py").read_text(
        encoding="utf-8"
    )
    button_style = (ROOT / "opencae/ui/core/styles/buttons.py").read_text(
        encoding="utf-8"
    )

    assert "background: rgba(255,255,255,0.012)" not in group_source
    assert "QFrame#RibbonGroup { background: transparent;" in group_source
    assert 'widget.setProperty("resultsRibbonButton", True)' in group_source
    assert 'QToolButton[resultsRibbonButton="true"]' in button_style
    checked = button_style.split(
        'QToolButton[resultsRibbonButton="true"]:checked', 1
    )[1]
    assert "background: {p['panel_active']};" in checked
    assert "border-color: {p['accent']};" in checked


def test_browser_project_solution_tabs_have_dedicated_flat_style():
    panel_source = (ROOT / "opencae/ui/tree/project_panel.py").read_text(
        encoding="utf-8"
    )
    tab_style = (ROOT / "opencae/ui/core/styles/tabs.py").read_text(
        encoding="utf-8"
    )

    assert 'self.tabs.setObjectName("BrowserTabBar")' in panel_source
    assert "self.tabs.setDrawBase(False)" in panel_source
    assert "QTabBar#BrowserTabBar" in tab_style
    browser_style = tab_style.split("QTabBar#BrowserTabBar", 1)[1].split(
        "QTabBar#WorkspaceTabBar", 1
    )[0]
    assert "background: {p['panel']};" in browser_style
    assert "border-bottom: 2px solid {p['accent']};" in browser_style
    assert "qproperty-drawBase: false;" in browser_style
