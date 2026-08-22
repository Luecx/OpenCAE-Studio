"""Regression coverage for workflow ribbon, context menu and dialog behavior."""

import ast
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QDialog

from opencae.model.core import EntityRef
from opencae.model.entities.analysis import Analysis, AnalysisStep
from opencae.ui.dialogs.analysis_dialog import AnalysisDialog


ROOT = Path(__file__).resolve().parents[1]


def _ribbon_groups(relative_path):
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    module = ast.parse(source)
    groups = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        name = function.id if isinstance(function, ast.Name) else getattr(function, "attr", "")
        if name != "RibbonGroupSpec" or len(node.args) < 2:
            continue
        title = ast.literal_eval(node.args[0])
        actions = tuple(
            item.attr
            for item in node.args[1].elts
            if isinstance(item, ast.Attribute)
        )
        groups.append((title, actions))
    return groups


def test_executable_selector_contains_only_dropdown_and_title():
    source = (
        ROOT / "opencae/ui/core/widgets/entity_selector_bar.py"
    ).read_text(encoding="utf-8")

    assert "QVBoxLayout(self)" in source
    assert 'label.setObjectName("RibbonGroupTitle")' in source
    assert "layout.addWidget(self.selector)" in source
    assert "layout.addWidget(label)" in source
    assert source.index("layout.addWidget(self.selector)") < source.index(
        "layout.addWidget(label)"
    )
    assert "action_button" not in source
    assert "action_ids" not in source


def test_analysis_ribbon_separates_definition_and_execution_groups():
    assert _ribbon_groups("opencae/ui/ribbon/analysis_page.py") == [
        (
            "DEFINITION",
            ("ANALYSIS_NEW", "ANALYSIS_EDIT", "DELETE_SELECTED"),
        ),
        (
            "ANALYSIS",
            (
                "VALIDATE",
                "PREVIEW_DECK",
                "WRITE_DECK",
                "SOLVER_SETTINGS",
                "ANALYSIS_RUN",
            ),
        ),
    ]


def test_studies_ribbon_separates_definition_setup_and_execution_groups():
    assert _ribbon_groups("opencae/ui/ribbon/studies_page.py") == [
        (
            "DEFINITION",
            ("STUDY_NEW_TOPOLOGY", "STUDY_EDIT", "DELETE_SELECTED"),
        ),
        (
            "TOPOLOGY SETUP",
            (
                "OPT_RESPONSE",
                "OPT_OBJECTIVE",
                "OPT_CONSTRAINT",
                "OPT_FILTER",
                "OPT_SYMMETRY",
                "OPT_CONTROLS",
            ),
        ),
        (
            "STUDY",
            ("STUDY_VALIDATE", "STUDY_RUN"),
        ),
    ]


def test_steps_ribbon_does_not_expose_selected_edit_or_delete():
    source = (ROOT / "opencae/ui/ribbon/steps_page.py").read_text(
        encoding="utf-8"
    )

    assert "A.REORDER_STEPS" in source
    assert "A.STEP_MATRIX" in source
    assert "A.EDIT_SELECTED" not in source
    assert "A.DELETE_SELECTED" not in source


def test_context_menu_keeps_unavailable_actions_visible_but_disabled():
    source = (ROOT / "opencae/ui/tree/context_menu.py").read_text(
        encoding="utf-8"
    )

    assert "ids = tuple(MAP.get(kind, ()))" in source
    assert "action.setEnabled(bool(enabled and source.isEnabled()))" in source
    assert "available(action_id, store, kind)" in source
    assert "if available(action_id, store, kind)" not in source


def test_delete_uses_a_simple_close_icon():
    source = (ROOT / "opencae/ui/core/icons/factory.py").read_text(
        encoding="utf-8"
    )

    assert "if kind == IconKind.DELETE" in source
    assert "QStyle.StandardPixmap.SP_DialogCloseButton" in source
    assert "QStyle.StandardPixmap.SP_TrashIcon" not in source
    assert "IconKind.DELETE:LegacyKind.FIXED" not in source


def test_analysis_dialog_remains_usable_after_exec_returns():
    app = QApplication.instance() or QApplication([])
    step = AnalysisStep(name="Static", step_type="Linear Static")
    analysis = Analysis(
        name="Analysis-1",
        step_refs=[EntityRef.of(step, "AnalysisStep")],
    )
    dialog = AnalysisDialog(
        analysis,
        [step],
        ["FEMaster"],
        existing_names=(),
    )

    QTimer.singleShot(0, dialog.accept)
    result = dialog.exec()

    assert result == QDialog.DialogCode.Accepted
    assert dialog.validate()
    candidate = dialog.result()
    assert candidate.name == "Analysis-1"
    assert [reference.entity_id for reference in candidate.step_refs] == [step.id]
    dialog.deleteLater()
    app.processEvents()
