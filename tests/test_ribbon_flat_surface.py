"""Regression checks for the flat ribbon surface and selector separators."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ribbon_groups_and_buttons_share_the_host_surface():
    group = (ROOT / "opencae/ui/ribbon/ribbon_group.py").read_text(encoding="utf-8")
    buttons = (ROOT / "opencae/ui/core/styles/buttons.py").read_text(encoding="utf-8")

    assert '"background: transparent; "' in group
    assert "rgba(255,255,255,0.012)" not in group
    ribbon_rule = buttons.split('QToolButton[ribbonButton="true"] {', 1)[1].split("}", 1)[0]
    assert "background: transparent;" in ribbon_rule
    assert "border: 1px solid transparent;" in ribbon_rule


def test_leading_ribbon_selector_has_explicit_vertical_separator():
    page = (ROOT / "opencae/ui/ribbon/ribbon_page.py").read_text(encoding="utf-8")
    part = (ROOT / "opencae/ui/ribbon/part_page.py").read_text(encoding="utf-8")
    analysis = (ROOT / "opencae/ui/ribbon/analysis_page.py").read_text(encoding="utf-8")
    studies = (ROOT / "opencae/ui/ribbon/studies_page.py").read_text(encoding="utf-8")

    assert 'separator.setObjectName("RibbonLeadingSeparator")' in page
    assert "border-right: 1px solid" in page
    assert "_LEADING_SEPARATOR_WIDTH" in page
    assert "leading_widgets=(part_selector,)" in part
    assert "leading_widgets=(selector_bar,)" in analysis
    assert "leading_widgets=(selector_bar,)" in studies
