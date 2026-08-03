from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_element_control_target_uses_supported_display_keyword():
    path = ROOT / "opencae/ui/dialogs/element_control_target.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "SelectionMembersWidget"
    ]
    assert len(calls) == 1
    keywords = {keyword.arg for keyword in calls[0].keywords}
    assert "display" in keywords
    assert "formatter" not in keywords


def test_selection_members_widget_accepts_legacy_formatter_keyword():
    path = ROOT / "opencae/ui/core/widgets/selection_members.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    widget_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "SelectionMembersWidget")
    constructor = next(node for node in widget_class.body if isinstance(node, ast.FunctionDef) and node.name == "__init__")
    assert "formatter" in {argument.arg for argument in constructor.args.kwonlyargs}


def test_element_control_target_constructs_with_pyqt6():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    qt_widgets = pytest.importorskip("PyQt6.QtWidgets")
    from opencae.ui.dialogs.element_control_target import ElementControlTarget

    application = qt_widgets.QApplication.instance() or qt_widgets.QApplication([])
    widget = ElementControlTarget(selection_provider=lambda: (), element_sets=(), targets=())
    assert widget.targets() == []
    widget.close()
    application.processEvents()
